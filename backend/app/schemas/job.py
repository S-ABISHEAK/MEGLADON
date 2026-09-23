from datetime import datetime
from typing import Any

from pydantic import BaseModel


class JobCreateResponse(BaseModel):
    job_id: str
    status: str


class VideoMetadataOut(BaseModel):
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    duration: float | None = None
    codec: str | None = None
    bitrate: int | None = None
    frame_count: int | None = None
    has_gps_metadata: str | None = None

    class Config:
        from_attributes = True


class StageOut(BaseModel):
    stage: str
    status: str
    progress: float
    current_operation: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    stats: dict[str, Any] = {}
    demo_mode: str | None = None

    class Config:
        from_attributes = True


class JobOut(BaseModel):
    id: str
    filename: str
    status: str
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    failed_stage: str | None = None
    video_metadata: VideoMetadataOut | None = None
    stages: list[StageOut] = []

    class Config:
        from_attributes = True
