# ▶ YouTube Video Summarizer

Turn any YouTube video into clean, structured study notes in seconds. Paste a URL and an AI pipeline fetches the transcript, chunks it by timestamp, and uses OpenAI's `gpt-4o-mini` to produce a comprehensive summary — key points, actionable takeaways, topics, and difficulty — rendered in a calm, minimal React interface.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![OpenAI](https://img.shields.io/badge/OpenAI-gpt--4o--mini-412991?logo=openai&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)

---

## Architecture

```
   React + Vite (frontend)                    FastAPI (backend)
  ┌──────────────────────┐   POST /summarize  ┌──────────────────────────┐
  │  SearchBar           │ ─────────────────► │  1. parse video_id       │
  │  LoadingState        │   { url }          │  2. fetch transcript     │
  │  SummaryCard         │                    │     (yt-transcript-api   │
  │    ├ KeyPoints       │                    │      → yt-dlp fallback)  │
  │    └ Takeaways       │ ◄───────────────── │  3. chunk by ~5 min      │
  │                      │   { video_id,      │  4. guard 12k words      │
  │                      │     thumbnail_url, │  5. OpenAI gpt-4o-mini    │
  │                      │     processing,    │         │                │
  │                      │     summary }      │         ▼                │
  └──────────────────────┘                    │   structured JSON        │
                                              └──────────────────────────┘
```

---

## How it works

1. **URL** — User pastes a YouTube link. The frontend validates it client-side; the backend re-parses and sanitizes the video ID.
2. **Transcript** — `youtube-transcript-api` pulls captions, falling back to `yt-dlp` for auto-generated or translated subtitles when needed.
3. **Chunking** — The transcript is grouped into ~5-minute segments with `MM:SS` timestamps so the model can cite where each point comes from.
4. **Guard** — Transcripts over 12,000 words are truncated (with a note) to stay within token limits and avoid overflow on long videos.
5. **GPT-4o-mini** — The chunked transcript is sent to OpenAI with `response_format=json_object`, returning a strict JSON schema. A lightweight repair pass fixes malformed JSON without re-sending the full transcript.
6. **Structured JSON** — title, one-liner, 6–12 key points (each with a detail), exactly 5 takeaways, sentiment, difficulty, read time, and topics.
7. **React UI** — Rendered as a thumbnail header, clickable timestamp cards (deep-linking into the video), a takeaways checklist, and topic pills — with a one-click "Copy Notes" export.

---

## Tech Stack

| Layer       | Technology                                          |
|-------------|-----------------------------------------------------|
| Backend     | Python 3.11+, FastAPI, Uvicorn                       |
| AI          | OpenAI `gpt-4o-mini` (`max_tokens=4000`, `temp=0.3`) |
| Transcripts | `youtube-transcript-api` + `yt-dlp` fallback        |
| Frontend    | React 18, Vite, pure CSS (no UI framework)          |
| Hardening   | `slowapi` rate limiting, startup env validation, scoped CORS |

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- An OpenAI API key

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                # then add your OPENAI_API_KEY
uvicorn main:app --reload --port 8000
```

The backend validates `OPENAI_API_KEY` on startup and refuses to boot if it's missing or malformed.

`.env` keys:

| Variable          | Description                                          |
|-------------------|------------------------------------------------------|
| `OPENAI_API_KEY`  | Your OpenAI key (must start with `sk-`).             |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins (defaults to localhost).|

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the printed Vite URL (default http://localhost:5173). Vite proxies `/summarize`, `/transcript-status`, and `/health` to the backend on port 8000, so no CORS config is needed in development.

---

## Screenshot

<!-- Add a screenshot of the app here, e.g. ![Screenshot](docs/screenshot.png) -->
_Screenshot placeholder — drop a capture of the summary view here._

---

## Production Notes

- **Rate limiting** — `/summarize` is capped at 10 requests/minute per IP via `slowapi`.
- **CORS** — Locked to the origins listed in `ALLOWED_ORIGINS`, not `*`.
- **Input sanitization** — URLs are length-capped and parsed against strict YouTube patterns before any network call.
- **Token safety** — 12,000-word transcript guard plus a 4,000-token completion budget prevent mid-sentence truncation.
- **Friendly errors** — All failures surface as readable messages, never raw stack traces.
