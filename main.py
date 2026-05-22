import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from models import SummarizeRequest, SummaryResponse, TranscriptStatusResponse
from summarizer import get_transcript_status, summarize_youtube_video


load_dotenv()

app = FastAPI(title="YouTube Video Summarizer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": "Invalid request. Provide a non-empty URL."})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    status_code = getattr(exc, "status_code", 500)
    message = getattr(exc, "detail", str(exc))
    return JSONResponse(status_code=status_code, content={"error": message})


@app.get("/")
async def root() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/summarize", response_model=SummaryResponse)
async def summarize(request: SummarizeRequest) -> SummaryResponse:
    start_time = time.perf_counter()
    video_id, summary = summarize_youtube_video(request.url)
    processing_time = round(time.perf_counter() - start_time, 2)

    return SummaryResponse(
        **summary,
        video_id=video_id,
        processing_time_seconds=processing_time,
    )


@app.post("/transcript-status", response_model=TranscriptStatusResponse)
async def transcript_status(request: SummarizeRequest) -> TranscriptStatusResponse:
    return TranscriptStatusResponse(**get_transcript_status(request.url))
