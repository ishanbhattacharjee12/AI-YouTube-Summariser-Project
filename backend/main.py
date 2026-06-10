import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from models import SummarizeRequest, SummaryResponse, TranscriptStatusResponse
from summarizer import get_transcript_status, summarize_youtube_video

load_dotenv()

# ── Startup validation ────────────────────────────────────────────────────────
_api_key = os.getenv("OPENAI_API_KEY", "")
if not _api_key or not _api_key.startswith("sk-"):
    raise RuntimeError(
        "OPENAI_API_KEY is missing or invalid in .env. "
        "Add a valid key that starts with 'sk-'."
    )

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="YouTube Video Summarizer", version="2.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
_allowed_origins = [origin.strip() for origin in _raw_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ── Exception handlers ────────────────────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": "Invalid request. Please provide a YouTube URL."})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    status_code = getattr(exc, "status_code", 500)
    message = getattr(exc, "detail", "An unexpected error occurred. Please try again.")
    return JSONResponse(status_code=status_code, content={"error": message})


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/summarize", response_model=SummaryResponse)
@limiter.limit("10/minute")
async def summarize(request: Request, body: SummarizeRequest) -> SummaryResponse:
    start_time = time.perf_counter()
    video_id, summary = summarize_youtube_video(body.url)
    processing_time = round(time.perf_counter() - start_time, 2)

    return SummaryResponse(
        video_id=video_id,
        thumbnail_url=f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        processing_time_seconds=processing_time,
        summary=summary,
    )


@app.post("/transcript-status", response_model=TranscriptStatusResponse)
async def transcript_status(body: SummarizeRequest) -> TranscriptStatusResponse:
    return TranscriptStatusResponse(**get_transcript_status(body.url))
