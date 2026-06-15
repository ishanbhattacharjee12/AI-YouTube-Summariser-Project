# AI YouTube Summarizer

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![OpenAI](https://img.shields.io/badge/OpenAI-gpt--4o--mini-412991?logo=openai&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

> **🚀 Live Demo:** [https://ai-you-tube-summariser-project.vercel.app](https://ai-you-tube-summariser-project.vercel.app/)  
> **⚙️ Backend API Docs:** [https://ai-youtube-summariser-project.onrender.com/docs](https://ai-youtube-summariser-project.onrender.com/docs)

---

## 📖 Project Overview

AI YouTube Summarizer is a full-stack application designed to instantly transform any long-form YouTube video into structured, actionable study notes. By leveraging modern LLMs (`gpt-4o-mini`), the system intelligently extracts the video transcript, chunks it by time segments, and distills the content into key takeaways, topics, and timestamped bullet points. 

Built with a clean, minimal React interface and a high-performance FastAPI backend, this tool is designed for students, researchers, and professionals who want to consume video content exponentially faster.

---

## ✨ Features

- **Instant AI Summarization**: Turn 1-hour lectures into 2-minute reads.
- **Timestamped Deep Linking**: Every key point links directly to the exact moment in the YouTube video.
- **Actionable Takeaways**: Automatically extracts the 5 most important, actionable lessons from the video.
- **Resilient Extraction Pipeline**: Falls back to `yt-dlp` for videos with auto-generated or translated subtitles.
- **Graceful Fallback & Caching**: Guarantees 100% uptime for core showcase videos even when YouTube throttles datacenter IPs.
- **Security First**: Input sanitization, strict CORS policies, and `slowapi` rate-limiting.

---

## 🏗 System Architecture

The application operates via asynchronous REST API calls between a Vite-optimized React frontend and a FastAPI backend.

```text
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

---

## 🛠 Tech Stack

| Layer       | Technology                                          |
|-------------|-----------------------------------------------------|
| **Backend** | Python 3.11, FastAPI, Uvicorn, Pydantic             |
| **AI**      | OpenAI API (`gpt-4o-mini`), Token chunking          |
| **Scraping**| `youtube-transcript-api`, `yt-dlp`                  |
| **Frontend**| React 18, Vite, Pure CSS (No heavy CSS frameworks)  |
| **DevOps**  | Docker, Docker Compose, Vercel, Render              |

---

## 📂 Project Structure

```text
├── frontend/                  # React + Vite frontend application
│   ├── public/                # Static assets (Favicons)
│   ├── src/
│   │   ├── components/        # Modular UI components (Hero, SummaryCard, etc.)
│   │   ├── App.jsx            # Main application layout and state
│   │   └── main.jsx           # React DOM entry point
│   └── package.json           # Frontend dependencies
│
├── backend/                   # FastAPI backend application
│   ├── demo_cache/            # Pre-fetched JSON transcripts for graceful degradation
│   ├── main.py                # FastAPI entry point, routing, and CORS
│   ├── models.py              # Pydantic schema validation models
│   ├── summarizer.py          # Core business logic: Extraction, Chunking, and OpenAI integration
│   ├── Dockerfile             # Production container definition
│   └── requirements.txt       # Python dependencies
│
├── render.yaml                # Render Blueprint deployment configuration
├── docker-compose.yml         # Local/VPS orchestration configuration
└── README.md
```

---

## 🚀 Backend API Documentation

The backend exposes a highly robust, documented REST API. You can view the interactive Swagger UI by visiting `/docs` on the live backend URL.

### `POST /summarize`
**Description**: Accepts a YouTube URL, extracts the transcript, and returns an AI-generated summary.

**Request Body**:
```json
{
  "url": "https://www.youtube.com/watch?v=..."
}
```

**Success Response (200 OK)**:
```json
{
  "video_id": "...",
  "thumbnail_url": "...",
  "title": "...",
  "read_time": "...",
  "sentiment": "...",
  "topics": ["..."],
  "key_points": [
    { "timestamp": "01:23", "text": "..." }
  ],
  "takeaways": ["..."]
}
```

### `GET /health`
**Description**: Returns `{"status": "ok"}`. Used for load balancer and deployment health checks.

---

## 🌩 Deployment Architecture

This repository is built for ultimate flexibility, supporting both modern Serverless PaaS and traditional VPS deployments.

- **Frontend**: Deployed on **Vercel** with a global edge CDN for instantaneous load times.
- **Backend**: Deployed as a web service on **Render**, dynamically bound to the `$PORT` environment variable.
- **Containerization**: Fully Dockerized via `docker-compose.yml`, allowing the entire backend to be dropped into any generic VPS (e.g., AWS EC2, Google Cloud Compute) with a single command.

---

## 🛑 Challenges Faced & Solutions

### The Challenge: Aggressive Datacenter IP Blocking
When deploying the backend to shared cloud providers (like Render or AWS), YouTube's automated anti-bot systems aggressively flag and block the datacenter's IP address, throwing `HTTP 429` or `Sign in to confirm you're not a bot` errors during transcript extraction.

### The Solution: Transcript Caching & Graceful Degradation
To guarantee that the application's core functionality—the AI summarization and UI—is always available, I implemented a **Graceful Degradation Architecture**:
1. **Pre-Fetched Caching**: Transcripts for core showcase videos are safely cached on the backend (`backend/demo_cache`).
2. **Local Intercept**: When a user selects a showcase video, the backend intercepts the request and reads the transcript locally, completely bypassing YouTube's network blocks.
3. **Graceful Fallback UI**: If a user pastes a custom video and YouTube blocks the cloud server, the backend catches the specific `IpBlocked` exception and returns a custom 429 response. The frontend then gracefully informs the user that live extraction is throttled, directing them to the fully functional cached videos.

This guarantees **100% uptime** for the AI demonstration, regardless of external third-party outages or strict anti-scraping measures.

---

## 💻 Setup & Installation

### Prerequisites
- Node.js 18+
- Python 3.11+
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

Add your `OPENAI_API_KEY` to `.env`.

```bash
# Start the server locally
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend
npm install

# Start the dev server
npm run dev
```

---

## 🚢 VPS Deployment Instructions (Docker)

If you wish to deploy the backend to a dedicated Virtual Private Server (VPS) to bypass shared datacenter IP bans permanently:

1. Install Docker and Docker Compose on your server.
2. Clone this repository.
3. In the root directory, create a `.env` file:
   ```env
   OPENAI_API_KEY=your_key_here
   ALLOWED_ORIGINS=https://your-frontend-domain.com
   ```
4. Run `docker-compose up -d`. The backend is now live on port `8000`.

---

## 📸 Screenshots

![Landing Page](README_Screenshots/Screenshot%202.png)
*Clean, minimal landing page focusing on the core user action.*

![Loading State](README_Screenshots/Screenshot%201.png)
*Status indicators keep the user informed during the 10-15s AI processing window.*

![Key Takeaways](README_Screenshots/Screenshot%203.png)
*Actionable takeaways and high-level video metadata.*

![Timestamped Key Points](README_Screenshots/Screenshot%205.png)
*Detailed, chronological notes featuring deep links back to the original video.*

---

## 🔮 Future Improvements

- **User Accounts & OAuth**: Allow users to save their generated summaries to a personal database.
- **Export Capabilities**: 1-click export to Notion, Obsidian, and PDF formats.
- **Custom Prompts**: Let users choose between "Detailed Notes", "Brief Overview", or "Action Items Only".
- **Whisper Integration**: Add support for passing video audio directly to OpenAI Whisper for videos that have no captions enabled.

---

## 📄 License
This project is licensed under the MIT License.
