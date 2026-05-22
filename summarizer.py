import json
import os
import re
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import HTTPException
import requests
from requests import RequestException
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


VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
YOUTUBE_PATTERNS = [
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/watch\?(?:.*&)?v=([A-Za-z0-9_-]{11})(?:[&#?].*)?$"),
    re.compile(r"(?:https?://)?(?:www\.)?youtu\.be/([A-Za-z0-9_-]{11})(?:[?&#/].*)?$"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([A-Za-z0-9_-]{11})(?:[?&#/].*)?$"),
]

SYSTEM_PROMPT = (
    "You are an expert content summarizer. Given a YouTube video transcript "
    "with timestamps, produce a structured summary. Always respond in valid "
    "JSON only — no markdown, no extra text."
)

PREFERRED_LANGUAGE_CODES = ["en", "en-US", "en-GB", "hi", "hi-IN"]
PREFERRED_SUBTITLE_EXTENSIONS = ["json3", "vtt", "srv3", "srv2", "srv1", "ttml"]
YOUTUBE_VIDEOS_API_URL = "https://www.googleapis.com/youtube/v3/videos"
GEMINI_API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_MODEL = "gemini-2.0-flash"
STOPWORDS = {
    "a",
    "about",
    "after",
    "again",
    "all",
    "also",
    "am",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "just",
    "like",
    "more",
    "most",
    "not",
    "of",
    "on",
    "or",
    "our",
    "out",
    "so",
    "that",
    "the",
    "their",
    "then",
    "there",
    "these",
    "they",
    "this",
    "to",
    "up",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "will",
    "with",
    "you",
    "your",
}

load_dotenv()


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
        detail="Invalid YouTube URL or video ID. Use youtube.com/watch?v=ID, youtu.be/ID, youtube.com/shorts/ID, or an 11-character video ID.",
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
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
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
        timing_index = next((index for index, line in enumerate(lines) if "-->" in line), None)
        if timing_index is None:
            continue

        timing = lines[timing_index]
        start_raw, end_raw = [part.strip().split()[0] for part in timing.split("-->", 1)]
        start = _parse_vtt_time(start_raw)
        end = _parse_vtt_time(end_raw)
        text = _clean_caption_text(" ".join(lines[timing_index + 1 :]))
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
    }
    with YoutubeDL(options) as ydl:
        return ydl.extract_info(url, download=False)


def _get_youtube_video_status(video_id: str) -> Optional[dict[str, Any]]:
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key or api_key == "your_youtube_api_key_here":
        return None

    response = requests.get(
        YOUTUBE_VIDEOS_API_URL,
        params={
            "part": "snippet,status,contentDetails",
            "id": video_id,
            "key": api_key,
        },
        timeout=15,
    )
    if response.status_code in {400, 401, 403}:
        return {
            "exists": None,
            "message": "The configured YouTube API key could not be used. Enable YouTube Data API v3 for the Google Cloud project and check key restrictions/quota.",
        }
    response.raise_for_status()
    payload = response.json()
    items = payload.get("items", [])

    if not items:
        return {
            "exists": False,
            "message": "The YouTube Data API could not find this video. It may be private, deleted, region-blocked, or unavailable.",
        }

    item = items[0]
    snippet = item.get("snippet", {})
    status = item.get("status", {})
    return {
        "exists": True,
        "title": snippet.get("title"),
        "channel_title": snippet.get("channelTitle"),
        "privacy_status": status.get("privacyStatus"),
        "embeddable": status.get("embeddable"),
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
        f"{fallback_message} YouTube Data API can see \"{title}\", "
        "so the video exists, but captions are not exposed to transcript tools."
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
            "message": "No accessible YouTube subtitle tracks were found for this video.",
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

    manual_transcripts = [item for item in transcripts if not getattr(item, "is_generated", False)]
    generated_transcripts = [item for item in transcripts if getattr(item, "is_generated", False)]

    for language_code in PREFERRED_LANGUAGE_CODES:
        for transcript in manual_transcripts:
            if getattr(transcript, "language_code", "") == language_code:
                return transcript, False
        for transcript in generated_transcripts:
            if getattr(transcript, "language_code", "") == language_code:
                return transcript, False

    english_translatable = next(
        (
            transcript
            for transcript in transcripts
            if getattr(transcript, "is_translatable", False)
            and any(language.get("language_code") == "en" for language in getattr(transcript, "translation_languages", []))
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
            "languages": [_transcript_label(transcript) for transcript in transcripts],
            "message": "Subtitles are available and can be summarized.",
        }
    except (TranscriptsDisabled, NoTranscriptFound, ValueError):
        try:
            return _get_yt_dlp_status(video_id)
        except DownloadError as exc:
            message = _diagnostic_message(video_id, f"YouTube could not provide this video to the app: {exc}")
            return {
                "video_id": video_id,
                "available": False,
                "transcript_count": 0,
                "languages": [],
                "message": message,
            }
        except (RequestException, ValueError):
            message = _diagnostic_message(video_id, "No accessible YouTube captions were found for this video.")
            return {
                "video_id": video_id,
                "available": False,
                "transcript_count": 0,
                "languages": [],
                "message": message,
            }
    except (CouldNotRetrieveTranscript, VideoUnavailable):
        try:
            return _get_yt_dlp_status(video_id)
        except DownloadError as exc:
            message = _diagnostic_message(video_id, f"YouTube could not provide this video to the app: {exc}")
            return {
                "video_id": video_id,
                "available": False,
                "transcript_count": 0,
                "languages": [],
                "message": message,
            }
        except (RequestException, ValueError):
            message = _diagnostic_message(video_id, "YouTube did not allow transcript access for this video.")
            return {
                "video_id": video_id,
                "available": False,
                "transcript_count": 0,
                "languages": [],
                "message": message,
            }
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
    except (IpBlocked, RequestBlocked):
        raise HTTPException(
            status_code=429,
            detail=(
                "YouTube is blocking transcript requests from this network/session. "
                "Try again later, switch networks, or run from a normal home network. "
                "The app code is working, but YouTube refused transcript access."
            ),
        ) from None
    except (TranscriptsDisabled, NoTranscriptFound, ValueError):
        try:
            transcript, _metadata = _fetch_transcript_with_yt_dlp(video_id)
            return transcript
        except DownloadError as exc:
            message = _diagnostic_message(video_id, f"YouTube could not provide this video to the app: {exc}")
            raise HTTPException(
                status_code=400,
                detail=message,
            ) from None
        except (RequestException, ValueError):
            message = _diagnostic_message(
                video_id,
                "No accessible YouTube captions were found for this video. The app can summarize manual captions, auto-generated captions, and translated captions when YouTube exposes them.",
            )
            raise HTTPException(
                status_code=400,
                detail=message,
            ) from None
    except (CouldNotRetrieveTranscript, VideoUnavailable):
        try:
            transcript, _metadata = _fetch_transcript_with_yt_dlp(video_id)
            return transcript
        except DownloadError as exc:
            message = _diagnostic_message(video_id, f"YouTube could not provide this video to the app: {exc}")
            raise HTTPException(
                status_code=400,
                detail=message,
            ) from None
        except (RequestException, ValueError):
            message = _diagnostic_message(
                video_id,
                "YouTube did not allow transcript access for this video. Try a public video with visible captions/subtitles.",
            )
            raise HTTPException(
                status_code=400,
                detail=message,
            ) from None
    except RequestException as exc:
        raise HTTPException(
            status_code=400,
            detail="Network error while contacting YouTube. Check your internet connection and try again.",
        ) from exc
    except Exception as exc:
        try:
            transcript, _metadata = _fetch_transcript_with_yt_dlp(video_id)
            return transcript
        except DownloadError as fallback_exc:
            message = _diagnostic_message(video_id, f"YouTube could not provide this video to the app: {fallback_exc}")
            raise HTTPException(status_code=400, detail=message) from exc
        except (RequestException, ValueError):
            message = _diagnostic_message(
                video_id,
                "Transcript not available for this video.",
            )
            raise HTTPException(status_code=400, detail=message) from exc


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
            chunks.append(
                {
                    "timestamp": _format_timestamp(current_start),
                    "text": " ".join(current_text),
                }
            )
            current_start = start
            current_text = []

        current_text.append(text)

    if current_text:
        chunks.append(
            {
                "timestamp": _format_timestamp(current_start),
                "text": " ".join(current_text),
            }
        )

    return "\n\n".join(f"[{chunk['timestamp']}]\n{chunk['text']}" for chunk in chunks)


def _build_user_prompt(transcript_text: str) -> str:
    return f"""
Summarize this YouTube transcript. Return ONLY a JSON object:
{{
  "title_guess": "inferred video topic in ≤10 words",
  "one_liner": "single sentence capturing the core idea",
  "key_points": [
    {{"timestamp": "MM:SS", "point": "concise insight from this segment"}}
  ],
  "takeaways": ["actionable takeaway 1", "takeaway 2"],
  "sentiment": "educational | entertaining | motivational | technical | other",
  "estimated_read_time_minutes": <integer>
}}

TRANSCRIPT (with timestamps):
{transcript_text}
""".strip()


def _build_gemini_prompt(transcript_text: str) -> str:
    return f"{SYSTEM_PROMPT}\n\n{_build_user_prompt(transcript_text)}"


def _extract_json(raw_content: str) -> dict[str, Any]:
    content = raw_content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    return json.loads(content)


def _validate_summary_payload(payload: dict[str, Any]) -> dict[str, Any]:
    required_fields = {
        "title_guess",
        "one_liner",
        "key_points",
        "takeaways",
        "sentiment",
        "estimated_read_time_minutes",
    }
    missing = required_fields - payload.keys()
    if missing:
        raise ValueError(f"Missing fields: {', '.join(sorted(missing))}")
    return payload


def _split_transcript_chunks(transcript_text: str) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    matches = list(re.finditer(r"^\[(\d{2,}:\d{2})\]\n", transcript_text, flags=re.MULTILINE))

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(transcript_text)
        text = transcript_text[start:end].strip()
        if text:
            chunks.append({"timestamp": match.group(1), "text": text})

    if not chunks and transcript_text.strip():
        chunks.append({"timestamp": "00:00", "text": transcript_text.strip()})
    return chunks


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [sentence.strip() for sentence in sentences if len(sentence.strip()) > 30]


def _keywords(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9'-]{2,}", text.lower())
    return [word for word in words if word not in STOPWORDS and not word.isdigit()]


def _sentence_score(sentence: str, frequencies: dict[str, int]) -> float:
    words = _keywords(sentence)
    if not words:
        return 0.0
    return sum(frequencies.get(word, 0) for word in words) / max(8, len(words))


def _best_sentence(text: str, frequencies: dict[str, int]) -> str:
    sentences = _split_sentences(text)
    if not sentences:
        return text[:220].strip()
    return max(sentences, key=lambda sentence: _sentence_score(sentence, frequencies))[:260].strip()


def _estimate_sentiment(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ["tutorial", "learn", "explain", "guide", "course", "lesson"]):
        return "educational"
    if any(word in lowered for word in ["code", "api", "python", "javascript", "model", "data", "system"]):
        return "technical"
    if any(word in lowered for word in ["motivation", "mindset", "success", "improve", "growth"]):
        return "motivational"
    if any(word in lowered for word in ["funny", "story", "music", "movie", "game", "entertain"]):
        return "entertaining"
    return "educational"


def _local_summarize_transcript(transcript_text: str) -> dict[str, Any]:
    chunks = _split_transcript_chunks(transcript_text)
    full_text = " ".join(chunk["text"] for chunk in chunks)
    words = _keywords(full_text)
    frequencies: dict[str, int] = {}
    for word in words:
        frequencies[word] = frequencies.get(word, 0) + 1

    ranked_keywords = sorted(frequencies, key=frequencies.get, reverse=True)
    title_words = ranked_keywords[:6] or ["Video", "Summary"]
    title_guess = " ".join(word.capitalize() for word in title_words[:6])

    target_points = min(10, max(5, len(chunks)))
    if len(chunks) <= target_points:
        selected_chunks = chunks
    else:
        step = (len(chunks) - 1) / max(1, target_points - 1)
        indexes = sorted({round(index * step) for index in range(target_points)})
        selected_chunks = [chunks[index] for index in indexes]

    key_points = [
        {
            "timestamp": chunk["timestamp"],
            "point": _best_sentence(chunk["text"], frequencies),
        }
        for chunk in selected_chunks
    ]

    top_sentences = sorted(
        _split_sentences(full_text),
        key=lambda sentence: _sentence_score(sentence, frequencies),
        reverse=True,
    )
    one_liner = (
        top_sentences[0][:220].strip()
        if top_sentences
        else "This video discusses " + ", ".join(ranked_keywords[:5]) + "."
    )

    takeaways = []
    for sentence in top_sentences[1:8]:
        takeaway = sentence[:180].strip()
        if takeaway and takeaway not in takeaways:
            takeaways.append(takeaway)
        if len(takeaways) == 4:
            break

    while len(takeaways) < 3:
        keyword = ranked_keywords[len(takeaways)] if len(ranked_keywords) > len(takeaways) else "main idea"
        takeaways.append(f"Review the section on {keyword} and connect it to the video's main message.")

    estimated_read_time = max(1, round(len(full_text.split()) / 220))

    return {
        "title_guess": title_guess[:80],
        "one_liner": one_liner,
        "key_points": key_points,
        "takeaways": takeaways[:5],
        "sentiment": _estimate_sentiment(full_text),
        "estimated_read_time_minutes": estimated_read_time,
    }


def _call_gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("YOUTUBE_API_KEY")
    if not api_key or api_key in {"your_google_ai_studio_api_key_here", "your_youtube_api_key_here"}:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not configured. Add your Google AI Studio API key to .env.",
        )

    url = GEMINI_API_URL_TEMPLATE.format(model=GEMINI_MODEL)
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1500,
            "responseMimeType": "application/json",
        },
    }

    try:
        response = requests.post(url, params={"key": api_key}, json=payload, timeout=60)
    except RequestException as exc:
        raise HTTPException(
            status_code=500,
            detail="Network error while contacting Gemini. Check your internet connection and try again.",
        ) from exc

    if response.status_code in {400, 401, 403}:
        raise HTTPException(
            status_code=500,
            detail="Gemini rejected the API key or request. Make sure this is a Google AI Studio key with Gemini API access enabled.",
        )
    if response.status_code == 429:
        raise HTTPException(
            status_code=429,
            detail="Gemini rate limit reached. Wait a minute and try again.",
        )
    if not response.ok:
        raise HTTPException(
            status_code=500,
            detail=f"Gemini request failed with status {response.status_code}.",
        )

    data = response.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise HTTPException(status_code=500, detail="Gemini returned no summary candidates.")

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise HTTPException(status_code=500, detail="Gemini returned an empty summary.")
    return text


def summarize_transcript(transcript_text: str) -> dict[str, Any]:
    prompt = _build_gemini_prompt(transcript_text)
    try:
        first_content = _call_gemini(prompt)
    except HTTPException:
        return _local_summarize_transcript(transcript_text)

    try:
        return _validate_summary_payload(_extract_json(first_content))
    except (json.JSONDecodeError, ValueError):
        repair_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            "Fix this response so it is valid JSON only and matches the requested schema exactly. "
            "Do not include markdown or explanation.\n\n"
            f"Original request:\n{_build_user_prompt(transcript_text)}\n\n"
            f"Invalid response:\n{first_content}"
        )
        try:
            repair_content = _call_gemini(repair_prompt)
        except HTTPException:
            return _local_summarize_transcript(transcript_text)

        try:
            return _validate_summary_payload(_extract_json(repair_content))
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(
                status_code=500,
                detail="Failed to parse summary JSON from Gemini response.",
            ) from exc


def summarize_youtube_video(url_or_id: str) -> tuple[str, dict[str, Any]]:
    video_id = parse_video_id(url_or_id)
    transcript = fetch_transcript(video_id)
    transcript_text = chunk_transcript(transcript)
    summary = summarize_transcript(transcript_text)
    return video_id, summary
