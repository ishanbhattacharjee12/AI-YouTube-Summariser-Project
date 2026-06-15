import json
import logging
import os
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

from dotenv import load_dotenv
from fastapi import HTTPException
import requests
from requests import RequestException
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    CouldNotRetrieveTranscript,
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
)
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

load_dotenv()

VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
YOUTUBE_PATTERNS = [
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/watch\?(?:.*&)?v=([A-Za-z0-9_-]{11})(?:[&#?].*)?$"),
    re.compile(r"(?:https?://)?(?:www\.)?youtu\.be/([A-Za-z0-9_-]{11})(?:[?&#/].*)?$"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([A-Za-z0-9_-]{11})(?:[?&#/].*)?$"),
]

PREFERRED_LANGUAGE_CODES = ["en", "en-US", "en-GB", "hi", "hi-IN"]
PREFERRED_SUBTITLE_EXTENSIONS = ["json3", "vtt", "srv3", "srv2", "srv1", "ttml"]
YOUTUBE_VIDEOS_API_URL = "https://www.googleapis.com/youtube/v3/videos"
MAX_TRANSCRIPT_WORDS = 12000
TRUNCATION_NOTE = "\n\n[Transcript truncated to first 12,000 words for summarization]"

SYSTEM_PROMPT = (
    "You are an expert educational content analyst. Summarize YouTube video "
    "transcripts into detailed, structured notes. Your summaries must be "
    "comprehensive enough that someone could learn the topic without watching "
    "the video. Always respond with a valid JSON object only."
)


def _get_openai_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _build_user_prompt(transcript_text: str) -> str:
    return f"""Analyze this YouTube transcript and return a detailed JSON summary.
The summary must be comprehensive — if this is educational content,
the key points should work as study notes.

Return this exact JSON structure:
{{
  "title_guess": "Clear descriptive title in 8-10 words",
  "one_liner": "One complete sentence capturing the core message of the video.",
  "key_points": [
    {{
      "timestamp": "MM:SS",
      "point": "Detailed complete sentence explaining what is covered here.",
      "detail": "One additional sentence with a specific fact, example, or insight from this segment."
    }}
  ],
  "takeaways": [
    "Complete actionable sentence the viewer should remember or act on.",
    "Complete actionable sentence the viewer should remember or act on.",
    "Complete actionable sentence the viewer should remember or act on.",
    "Complete actionable sentence the viewer should remember or act on.",
    "Complete actionable sentence the viewer should remember or act on."
  ],
  "sentiment": "educational | entertaining | motivational | technical | news | other",
  "difficulty_level": "beginner | intermediate | advanced | general",
  "estimated_read_time_minutes": 3,
  "topics": ["topic1", "topic2", "topic3"]
}}

Rules:
- key_points: minimum 6, maximum 12 depending on video length
- takeaways: exactly 5, all complete sentences
- Every string must be a grammatically complete sentence
- point + detail together should give enough context to take notes from
- For technical/educational videos, include specific terms and concepts

TRANSCRIPT:
{transcript_text}"""


def parse_video_id(url_or_id: str) -> str:
    cleaned = url_or_id.strip()
    if VIDEO_ID_PATTERN.fullmatch(cleaned):
        return cleaned

    for pattern in YOUTUBE_PATTERNS:
        match = pattern.fullmatch(cleaned)
        if match:
            return match.group(1)

    raise HTTPException(
        status_code=422,
        detail="That doesn't look like a valid YouTube URL. Try a link like youtube.com/watch?v=... or youtu.be/...",
    )


def _format_timestamp(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    minutes = total_seconds // 60
    remaining_seconds = total_seconds % 60
    return f"{minutes:02d}:{remaining_seconds:02d}"


def _transcript_label(transcript: Any) -> str:
    language = getattr(transcript, "language", "Unknown")
    language_code = getattr(transcript, "language_code", "unknown")
    kind = "auto-generated" if getattr(transcript, "is_generated", False) else "manual"
    return f"{language} ({language_code}, {kind})"


def _list_transcripts(video_id: str) -> list[Any]:
    if hasattr(YouTubeTranscriptApi, "list_transcripts"):
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    else:
        transcript_list = YouTubeTranscriptApi().list(video_id)
    return list(transcript_list)


def _normalize_transcript_entries(entries: Any) -> list[dict[str, Any]]:
    normalized_entries: list[dict[str, Any]] = []
    for entry in entries:
        if isinstance(entry, dict):
            normalized_entries.append(entry)
            continue
        normalized_entries.append(
            {
                "text": getattr(entry, "text", ""),
                "start": getattr(entry, "start", 0.0),
                "duration": getattr(entry, "duration", 0.0),
            }
        )
    return normalized_entries


def _clean_caption_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_vtt_time(value: str) -> float:
    parts = value.strip().split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
    except ValueError:
        return 0.0
    return 0.0


def _parse_json3_subtitles(raw_content: str) -> list[dict[str, Any]]:
    payload = json.loads(raw_content)
    entries: list[dict[str, Any]] = []
    for event in payload.get("events", []):
        segments = event.get("segs") or []
        text = _clean_caption_text("".join(segment.get("utf8", "") for segment in segments))
        if not text:
            continue
        start = float(event.get("tStartMs", 0)) / 1000
        duration = float(event.get("dDurationMs", 0)) / 1000
        entries.append({"text": text, "start": start, "duration": duration})
    return entries


def _parse_vtt_subtitles(raw_content: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    blocks = re.split(r"\n\s*\n", raw_content.replace("\r\n", "\n"))
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing_index = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing_index is None:
            continue
        timing = lines[timing_index]
        start_raw, end_raw = [part.strip().split()[0] for part in timing.split("-->", 1)]
        start = _parse_vtt_time(start_raw)
        end = _parse_vtt_time(end_raw)
        text = _clean_caption_text(" ".join(lines[timing_index + 1:]))
        if text:
            entries.append({"text": text, "start": start, "duration": max(0.0, end - start)})
    return entries


def _fetch_subtitle_entries(subtitle_url: str, extension: str) -> list[dict[str, Any]]:
    response = requests.get(subtitle_url, timeout=20)
    response.raise_for_status()
    if extension == "json3":
        return _parse_json3_subtitles(response.text)
    return _parse_vtt_subtitles(response.text)


def _subtitle_label(language_code: str, subtitle: dict[str, Any], generated: bool) -> str:
    language_name = subtitle.get("name") or language_code
    kind = "auto-generated" if generated else "manual"
    return f"{language_name} ({language_code}, {kind})"


def _choose_yt_dlp_subtitle(info: dict[str, Any]) -> Optional[tuple[str, dict[str, Any], bool]]:
    manual_subtitles = info.get("subtitles") or {}
    generated_subtitles = info.get("automatic_captions") or {}

    for language_code in PREFERRED_LANGUAGE_CODES:
        if language_code in manual_subtitles:
            return language_code, {"tracks": manual_subtitles[language_code]}, False
        if language_code in generated_subtitles:
            return language_code, {"tracks": generated_subtitles[language_code]}, True

    if manual_subtitles:
        language_code = sorted(manual_subtitles.keys())[0]
        return language_code, {"tracks": manual_subtitles[language_code]}, False

    if generated_subtitles:
        language_code = sorted(generated_subtitles.keys())[0]
        return language_code, {"tracks": generated_subtitles[language_code]}, True

    return None


def _choose_subtitle_format(tracks: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    for extension in PREFERRED_SUBTITLE_EXTENSIONS:
        for track in tracks:
            if track.get("ext") == extension and track.get("url"):
                return track
    return next((track for track in tracks if track.get("url")), None)


def _get_yt_dlp_info(video_id: str) -> dict[str, Any]:
    url = f"https://www.youtube.com/watch?v={video_id}"
    options = {
        "quiet": True,
        "skip_download": True,
        "writesubtitles": False,
        "writeautomaticsub": False,
        "noplaylist": True,
        "extractor_args": {"youtube": {"player_client": ["android", "ios", "web"]}},
    }
    with YoutubeDL(options) as ydl:
        return ydl.extract_info(url, download=False)


def _get_youtube_video_status(video_id: str) -> Optional[dict[str, Any]]:
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key or api_key == "your_youtube_api_key_here":
        return None

    response = requests.get(
        YOUTUBE_VIDEOS_API_URL,
        params={"part": "snippet,status,contentDetails", "id": video_id, "key": api_key},
        timeout=15,
    )
    if response.status_code in {400, 401, 403}:
        return {
            "exists": None,
            "message": "The configured YouTube API key could not be used.",
        }
    response.raise_for_status()
    items = response.json().get("items", [])
    if not items:
        return {
            "exists": False,
            "message": "This video may be private, deleted, or region-blocked.",
        }
    item = items[0]
    snippet = item.get("snippet", {})
    status = item.get("status", {})
    return {
        "exists": True,
        "title": snippet.get("title"),
        "channel_title": snippet.get("channelTitle"),
        "privacy_status": status.get("privacyStatus"),
        "message": "The YouTube Data API can see this video.",
    }


def _diagnostic_message(video_id: str, fallback_message: str) -> str:
    try:
        video_status = _get_youtube_video_status(video_id)
    except RequestException:
        return fallback_message

    if not video_status:
        return fallback_message

    if video_status.get("exists") is None:
        return f"{fallback_message} {video_status['message']}"

    if not video_status.get("exists"):
        return video_status["message"]

    title = video_status.get("title") or "this video"
    return (
        f"{fallback_message} YouTube can see \"{title}\", "
        "but captions are not accessible for this video."
    )


def _fetch_transcript_with_yt_dlp(video_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    info = _get_yt_dlp_info(video_id)
    selected = _choose_yt_dlp_subtitle(info)
    if not selected:
        raise ValueError("No subtitles were exposed by yt-dlp.")

    language_code, subtitle_data, generated = selected
    track = _choose_subtitle_format(subtitle_data["tracks"])
    if not track:
        raise ValueError("No downloadable subtitle format was exposed by yt-dlp.")

    entries = _fetch_subtitle_entries(track["url"], track.get("ext", "vtt"))
    if not entries:
        raise ValueError("The selected subtitle track was empty.")

    metadata = {
        "selected_language": track.get("name") or language_code,
        "selected_language_code": language_code,
        "is_generated": generated,
        "is_translated": False,
        "source": "yt-dlp",
    }
    return entries, metadata


def _get_yt_dlp_status(video_id: str) -> dict[str, Any]:
    info = _get_yt_dlp_info(video_id)
    manual_subtitles = info.get("subtitles") or {}
    generated_subtitles = info.get("automatic_captions") or {}
    selected = _choose_yt_dlp_subtitle(info)
    languages = [
        _subtitle_label(code, tracks[0] if tracks else {}, False)
        for code, tracks in sorted(manual_subtitles.items())
    ] + [
        _subtitle_label(code, tracks[0] if tracks else {}, True)
        for code, tracks in sorted(generated_subtitles.items())
    ]

    if not selected:
        return {
            "video_id": video_id,
            "available": False,
            "transcript_count": 0,
            "languages": languages,
            "message": "No accessible subtitle tracks were found for this video.",
        }

    language_code, subtitle_data, generated = selected
    track = _choose_subtitle_format(subtitle_data["tracks"])
    return {
        "video_id": video_id,
        "available": track is not None,
        "selected_language": track.get("name") or language_code if track else language_code,
        "selected_language_code": language_code,
        "is_generated": generated,
        "is_translated": False,
        "transcript_count": len(manual_subtitles) + len(generated_subtitles),
        "languages": languages,
        "message": "Subtitles are available and can be summarized." if track else "Subtitle tracks exist, but no downloadable format was found.",
    }


def _choose_best_transcript(transcripts: list[Any]) -> tuple[Any, bool]:
    if not transcripts:
        raise ValueError("No transcripts were returned by YouTube.")

    manual = [t for t in transcripts if not getattr(t, "is_generated", False)]
    generated = [t for t in transcripts if getattr(t, "is_generated", False)]

    for language_code in PREFERRED_LANGUAGE_CODES:
        for t in manual:
            if getattr(t, "language_code", "") == language_code:
                return t, False
        for t in generated:
            if getattr(t, "language_code", "") == language_code:
                return t, False

    english_translatable = next(
        (
            t for t in transcripts
            if getattr(t, "is_translatable", False)
            and any(
                lang.get("language_code") == "en"
                for lang in getattr(t, "translation_languages", [])
            )
        ),
        None,
    )
    if english_translatable:
        return english_translatable.translate("en"), True

    return transcripts[0], False


def get_transcript_status(url_or_id: str) -> dict[str, Any]:
    video_id = parse_video_id(url_or_id)
    try:
        transcripts = _list_transcripts(video_id)
        selected_transcript, is_translated = _choose_best_transcript(transcripts)
        return {
            "video_id": video_id,
            "available": True,
            "selected_language": getattr(selected_transcript, "language", None),
            "selected_language_code": getattr(selected_transcript, "language_code", None),
            "is_generated": getattr(selected_transcript, "is_generated", None),
            "is_translated": is_translated,
            "transcript_count": len(transcripts),
            "languages": [_transcript_label(t) for t in transcripts],
            "message": "Subtitles are available and can be summarized.",
        }
    except (TranscriptsDisabled, NoTranscriptFound, ValueError):
        try:
            return _get_yt_dlp_status(video_id)
        except (DownloadError, RequestException, ValueError):
            message = _diagnostic_message(video_id, "No accessible YouTube captions were found for this video.")
            return {"video_id": video_id, "available": False, "transcript_count": 0, "languages": [], "message": message}
    except (CouldNotRetrieveTranscript, VideoUnavailable):
        try:
            return _get_yt_dlp_status(video_id)
        except (DownloadError, RequestException, ValueError):
            message = _diagnostic_message(video_id, "YouTube did not allow transcript access for this video.")
            return {"video_id": video_id, "available": False, "transcript_count": 0, "languages": [], "message": message}
    except RequestException:
        return {
            "video_id": video_id,
            "available": False,
            "transcript_count": 0,
            "languages": [],
            "message": "Network error while contacting YouTube. Check your internet connection and try again.",
        }


def fetch_transcript(video_id: str) -> list[dict[str, Any]]:
    try:
        transcripts = _list_transcripts(video_id)
        transcript, _is_translated = _choose_best_transcript(transcripts)
        return _normalize_transcript_entries(transcript.fetch())
    except (IpBlocked, RequestBlocked, TranscriptsDisabled, NoTranscriptFound, ValueError, CouldNotRetrieveTranscript, VideoUnavailable) as primary_exc:
        logger.warning(f"youtube-transcript-api failed for {video_id}: {type(primary_exc).__name__} - {primary_exc}")
        try:
            transcript, _metadata = _fetch_transcript_with_yt_dlp(video_id)
            return transcript
        except DownloadError as exc:
            logger.error(f"yt-dlp fallback failed for {video_id}: {exc}")
            error_str = str(exc).lower()
            if "http error 429" in error_str or "sign in to verify" in error_str or "bot" in error_str:
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "YouTube is aggressively blocking transcript requests from this cloud server. "
                        "Please try again later or host the backend on a different network."
                    ),
                ) from None
            message = _diagnostic_message(video_id, f"Could not retrieve this video: {exc}")
            raise HTTPException(status_code=400, detail=message) from None
        except (RequestException, ValueError) as exc:
            logger.error(f"yt-dlp metadata fetch failed for {video_id}: {exc}")
            message = _diagnostic_message(
                video_id,
                "No captions found or YouTube blocked access for this video.",
            )
            raise HTTPException(status_code=400, detail=message) from None
    except RequestException as exc:
        logger.error(f"Network error in primary fetch for {video_id}: {exc}")
        raise HTTPException(
            status_code=400,
            detail="Network error while contacting YouTube. Check your internet connection and try again.",
        ) from exc
    except Exception as exc:
        logger.error(f"Unexpected error in primary fetch for {video_id}: {exc}")
        try:
            transcript, _metadata = _fetch_transcript_with_yt_dlp(video_id)
            return transcript
        except (DownloadError, RequestException, ValueError) as fallback_exc:
            logger.error(f"Unexpected fallback error for {video_id}: {fallback_exc}")
            raise HTTPException(status_code=400, detail="Transcript not available for this video.") from fallback_exc


def chunk_transcript(transcript: list[dict[str, Any]], chunk_seconds: int = 300) -> str:
    if not transcript:
        raise HTTPException(status_code=400, detail="Transcript not available for this video.")

    chunks: list[dict[str, str]] = []
    current_start = float(transcript[0].get("start", 0.0))
    current_text: list[str] = []

    for entry in transcript:
        start = float(entry.get("start", 0.0))
        text = str(entry.get("text", "")).replace("\n", " ").strip()
        if not text:
            continue
        if current_text and start - current_start >= chunk_seconds:
            chunks.append({"timestamp": _format_timestamp(current_start), "text": " ".join(current_text)})
            current_start = start
            current_text = []
        current_text.append(text)

    if current_text:
        chunks.append({"timestamp": _format_timestamp(current_start), "text": " ".join(current_text)})

    return "\n\n".join(f"[{chunk['timestamp']}]\n{chunk['text']}" for chunk in chunks)


def _guard_transcript_length(transcript_text: str) -> str:
    words = transcript_text.split()
    if len(words) <= MAX_TRANSCRIPT_WORDS:
        return transcript_text
    truncated = " ".join(words[:MAX_TRANSCRIPT_WORDS])
    return truncated + TRUNCATION_NOTE


def _extract_json(raw_content: str) -> dict[str, Any]:
    content = raw_content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    return json.loads(content)


def _validate_summary_payload(payload: dict[str, Any]) -> dict[str, Any]:
    required_fields = {
        "title_guess", "one_liner", "key_points", "takeaways",
        "sentiment", "difficulty_level", "estimated_read_time_minutes", "topics",
    }
    missing = required_fields - payload.keys()
    if missing:
        raise ValueError(f"Missing fields: {', '.join(sorted(missing))}")

    # Validate and normalize timestamps on key_points
    ts_pattern = re.compile(r"^\d{2,}:\d{2}$")
    for point in payload.get("key_points", []):
        if not ts_pattern.match(point.get("timestamp", "")):
            point["timestamp"] = "00:00"
        if "detail" not in point:
            point["detail"] = ""

    return payload


def summarize_transcript(transcript_text: str) -> dict[str, Any]:
    guarded_text = _guard_transcript_length(transcript_text)
    user_prompt = _build_user_prompt(guarded_text)
    client = _get_openai_client()

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=4000,
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as exc:
        error_msg = str(exc)
        if "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
            raise HTTPException(status_code=500, detail="OpenAI API key is invalid or expired. Check your .env file.") from exc
        if "rate_limit" in error_msg.lower():
            raise HTTPException(status_code=429, detail="OpenAI rate limit reached. Please wait a moment and try again.") from exc
        raise HTTPException(status_code=500, detail="Failed to reach the AI service. Check your internet connection and try again.") from exc

    raw_content = response.choices[0].message.content or ""

    try:
        return _validate_summary_payload(_extract_json(raw_content))
    except (json.JSONDecodeError, ValueError):
        # Repair pass — only send the malformed JSON, not the full transcript
        repair_prompt = (
            "The following JSON is malformed or missing required fields. "
            "Fix it so it is valid JSON matching the requested schema exactly. "
            "Do not include markdown, explanation, or extra text. "
            "Required fields: title_guess, one_liner, key_points (list with timestamp/point/detail), "
            "takeaways (list of 5 strings), sentiment, difficulty_level, estimated_read_time_minutes (int), topics (list).\n\n"
            f"Malformed JSON:\n{raw_content}"
        )
        try:
            repair_response = client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=4000,
                temperature=0.0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": repair_prompt},
                ],
            )
            repaired = repair_response.choices[0].message.content or ""
            return _validate_summary_payload(_extract_json(repaired))
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail="The AI returned an unexpected response format. Please try again.",
            ) from exc


def summarize_youtube_video(url_or_id: str) -> tuple[str, dict[str, Any]]:
    video_id = parse_video_id(url_or_id)
    transcript = fetch_transcript(video_id)
    transcript_text = chunk_transcript(transcript)
    summary = summarize_transcript(transcript_text)
    return video_id, summary
