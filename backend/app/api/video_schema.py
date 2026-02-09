"""Pydantic schemas for the video inference API (P13)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.api.schema import Detection


# ---------- per-frame ----------

class FrameDetectionResult(BaseModel):
    """Detection results for a single video frame."""

    frame_index: int = Field(
        ..., description="0-based frame index",
    )
    timestamp_ms: float = Field(..., description="Position in video (ms)")
    detections: list[Detection] = Field(default_factory=list)
    privacy_applied: bool = False
    privacy_faces: int = 0


# ---------- summary ----------

class VideoSummary(BaseModel):
    """Aggregated statistics over all analysed frames."""

    total_frames_analysed: int = 0
    total_detections: int = 0
    unique_labels: list[str] = Field(default_factory=list)
    label_counts: dict[str, int] = Field(default_factory=dict)
    privacy_total_faces: int = 0


# ---------- job ----------

class VideoJobStatus(BaseModel):
    """Status of an async video-inference job."""

    job_id: str
    status: str = Field(
        default="queued",
        description="queued | processing | done | error",
    )
    progress: float = Field(
        default=0.0,
        description="0.0 – 1.0",
    )
    frames_done: int = 0
    frames_total: int = 0
    error: str | None = None


# ---------- full response ----------

class VideoInferResponse(BaseModel):
    """Complete response from a video inference job."""

    job_id: str
    status: str  # done | error
    video_width: int = 0
    video_height: int = 0
    fps: float = 0.0
    duration_ms: float = 0.0
    frame_interval: int = 1
    frames: list[FrameDetectionResult] = Field(default_factory=list)
    summary: VideoSummary = Field(default_factory=VideoSummary)
    error: str | None = None


# ---------- export ----------

class VideoExportStatus(BaseModel):
    """Status of a video render/export job."""

    job_id: str
    render_status: str = Field(
        default="not_started",
        description="not_started | queued | rendering | done | error",
    )
    render_error: str | None = None
