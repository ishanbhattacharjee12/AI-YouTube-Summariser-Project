# AI YouTube Summarizer

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![OpenAI](https://img.shields.io/badge/OpenAI-gpt--4o--mini-412991?logo=openai&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Overview

AI YouTube Summarizer is a powerful full-stack application that transforms any YouTube video into clean, structured study notes. By simply pasting a YouTube URL, the application leverages an AI pipeline to fetch the transcript, chunk it intelligently, and generate a comprehensive summary using OpenAI's `gpt-4o-mini`. 

Designed with a calm, minimal React interface, the application extracts key points, actionable takeaways, topics, and difficulty levels in seconds. It serves as an essential tool for students, researchers, and professionals who want to consume video content efficiently.

## Features

- **Instant Summarization**: Get detailed study notes from long YouTube videos in seconds.
- **Timestamped Key Points**: Deep-linking directly into the video for every summarized key point.
- **Actionable Takeaways**: Extracts exactly 5 actionable takeaways from the video content.
- **Smart Chunking Pipeline**: Intelligently groups transcripts into ~5-minute segments for contextual accuracy.
- **Robust Error Handling**: Graceful fallback to `yt-dlp` for auto-generated/translated subtitles.
- **Clean UI**: A responsive, pure CSS frontend built on React and Vite.
- **Security & Rate Limiting**: Features `slowapi` rate limiting and strict CORS/input sanitization.

---

## Architecture

The project consists of a **React + Vite** frontend and a **FastAPI** backend, communicating asynchronously.

```
   React + Vite (Frontend)                    FastAPI (Backend)
  ┌──────────────────────┐   POST /summarize  ┌──────────────────────────┐
  │  SearchBar           │ ─────────────────► │  1. Parse video ID       │
  │  LoadingState        │   { url }          │  2. Fetch transcript     │
  │  SummaryCard         │                    │     (yt-transcript-api   │
  │    ├ KeyPoints       │                    │      → yt-dlp fallback)  │
  │    └ Takeaways       │ ◄───────────────── │  3. Chunk by ~5 min      │
  │                      │   { video_id,      │  4. Guard 12k words      │
  │                      │     thumbnail_url, │  5. OpenAI gpt-4o-mini    │
  │                      │     processing,    │         │                │
  │                      │     summary }      │         ▼                │
  └──────────────────────┘                    │   Structured JSON        │
                                              └──────────────────────────┘
```

1. **URL Validation** — Client-side validation; backend re-parses and sanitizes the video ID.
2. **Transcript Extraction** — Uses `youtube-transcript-api`, falling back to `yt-dlp` for auto-generated or translated subtitles.
3. **Data Chunking** — The transcript is grouped into 5-minute segments with `MM:SS` timestamps.
4. **Token Management** — Transcripts over 12,000 words are guarded to stay within token limits.
5. **AI Processing** — OpenAI strictly formats the response as a JSON object containing the title, key points, takeaways, sentiment, read time, and topics.

---

## Tech Stack

| Layer       | Technology                                          |
|-------------|-----------------------------------------------------|
| **Backend** | Python 3.11+, FastAPI, Uvicorn                      |
| **AI**      | OpenAI `gpt-4o-mini` (`max_tokens=4000`)            |
| **Parsing** | `youtube-transcript-api`, `yt-dlp`                  |
| **Frontend**| React 18, Vite, pure CSS                            |
| **Security**| `slowapi` rate limiting, scoped CORS                |

---

## Setup & Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- An active OpenAI API key

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure Environment Variables
cp .env.example .env
```

Add your `OPENAI_API_KEY` to the newly created `.env` file. The backend will refuse to boot if it's missing or malformed.

```bash
# Start the Backend Server
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend
npm install

# Start the Development Server
npm run dev
```

Open the Vite URL (default `http://localhost:5173`). Vite is configured to proxy `/summarize` and `/health` to the backend on port 8000, so no additional CORS configuration is needed in development.

---

## Environment Variables

| Variable          | Description                                          |
|-------------------|------------------------------------------------------|
| `OPENAI_API_KEY`  | Your OpenAI key (must start with `sk-`).             |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins (defaults to localhost).|

---

## Screenshots

![Loading State](README_Screenshots/Screenshot%201.png)
*Processing a video with real-time status updates.*

![Landing Page](README_Screenshots/Screenshot%202.png)
*Clean, simple interface to quickly summarize any YouTube video.*

![Key Takeaways](README_Screenshots/Screenshot%203.png)
*Automatically generated actionable takeaways.*

![Timestamped Key Points](README_Screenshots/Screenshot%205.png)
*Detailed, timestamped notes that deep-link directly into the video.*

---

## Future Improvements

- Add user authentication and saved summaries history.
- Implement specialized summarization profiles (e.g. "Podcast", "Lecture", "Tutorial").
- Add multi-language support for transcripts and summaries.
- Export to Notion and PDF integrations.

## License

This project is licensed under the MIT License.
