## Setup
1. Clone repo
2. `python3 -m venv venv && source venv/bin/activate` (Windows: `venv\Scripts\activate`)
3. `pip install -r requirements.txt`
4. Copy `.env.example` → `.env`, add your Google AI Studio key

`GEMINI_API_KEY` enables AI summaries with Google Gemini. If Gemini is rate-limited or unavailable, the app automatically falls back to a free local extractive summarizer so the demo still runs. `YOUTUBE_API_KEY` is optional and is used only to diagnose whether a video is unavailable/private/deleted when transcript tools cannot access captions. If you use the same Google key for both, put it in both variables.

## Run
`uvicorn main:app --reload`
Open http://localhost:8000

Or run everything with:

`./run.sh`

## How It Works
The app accepts a YouTube URL or video ID, validates it, extracts the 11-character video ID, and fetches captions through `youtube-transcript-api`. If that fails, it falls back to `yt-dlp` for manual and auto-generated subtitle tracks. It prefers English transcripts, then Hindi, then translated English when available, then falls back to the first available language. Transcript entries are grouped into roughly five-minute timestamped chunks so the final summary can point back to useful moments in the video.

Those chunks are sent to Google Gemini with a strict JSON-only prompt using `gemini-2.0-flash`. The backend validates and repairs the JSON response if needed, then falls back to a local extractive summarizer if Gemini is unavailable or rate-limited. The API adds metadata like the video ID and processing time and returns it to the vanilla HTML/CSS/JS frontend for rendering with thumbnail, key-point timestamp links, takeaways, and clipboard-friendly formatted text. If a YouTube API key is configured, the backend also uses YouTube Data API as a diagnostic layer to explain unavailable/private videos more clearly.

## Notes
- Works only on videos with auto-generated or manual captions
- Gemini API key gives better summaries; local fallback works without paid APIs
- YouTube API key is optional for diagnostics
- Processing time ~5–15 seconds depending on video length
