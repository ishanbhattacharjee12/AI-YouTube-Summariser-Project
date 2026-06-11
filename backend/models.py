from typing import Optional

from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)


class KeyPoint(BaseModel):
    timestamp: str
    point: str
    detail: str


class SummaryPayload(BaseModel):
    title_guess: str
    one_liner: str
    key_points: list[KeyPoint]
    takeaways: list[str]
    sentiment: str
    difficulty_level: str
    estimated_read_time_minutes: int
    topics: list[str]


class SummaryResponse(BaseModel):
    video_id: str
    thumbnail_url: str
    processing_time_seconds: float
    summary: SummaryPayload


class TranscriptStatusResponse(BaseModel):
    video_id: str
    available: bool
    selected_language: Optional[str] = None
    selected_language_code: Optional[str] = None
    is_generated: Optional[bool] = None
    is_translated: bool = False
    transcript_count: int = 0
    languages: list[str] = []
    message: str

    
