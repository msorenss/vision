"""Pydantic schemas for Training API (P10)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ============ Training Configuration ============

class TrainingConfig(BaseModel):
    """Configuration for a training job."""
    
    dataset: str = Field(..., description="Dataset name to train on")
    epochs: int = Field(default=100, ge=1, le=1000, description="Number of training epochs")
    batch_size: int = Field(default=16, ge=1, le=128, description="Batch size")
    img_size: int = Field(default=640, ge=32, le=1280, description="Image size for training")
    model_variant: Literal["yolov8n", "yolov8s", "yolov8m", "yolov8l", "yolov8x"] = Field(
        default="yolov8n",
        description="YOLO model variant"
    )
    pretrained: bool = Field(default=True, description="Use pretrained weights")
    device: str = Field(default="cpu", description="Device: cpu, cuda, 0, 1, etc.")
    
    # Output
    bundle_name: str | None = Field(None, description="Output bundle name (default: dataset name)")
    bundle_version: str = Field(default="v1", description="Output bundle version")
    
    # Advanced
    patience: int = Field(default=50, ge=0, description="Early stopping patience (0=disabled)")
    lr0: float = Field(default=0.01, ge=0.0001, le=1.0, description="Initial learning rate")
    augment: bool = Field(default=True, description="Enable augmentation")


# ============ Training Status ============

class TrainingMetrics(BaseModel):
    """Training metrics at a point in time."""
    
    epoch: int
    box_loss: float | None = None
    cls_loss: float | None = None
    dfl_loss: float | None = None
    precision: float | None = None
    recall: float | None = None
    map50: float | None = None
    map50_95: float | None = None


class TrainingStatus(BaseModel):
    """Current status of a training job."""
    
    job_id: str
    status: Literal["queued", "running", "completed", "failed", "stopped"] = "queued"
    dataset: str
    
    # Progress
    current_epoch: int = 0
    total_epochs: int = 0
    progress_percent: float = 0.0
    
    # Timing
    started_at: str | None = None
    finished_at: str | None = None
    elapsed_seconds: float = 0.0
    eta_seconds: float | None = None
    
    # Results
    metrics: TrainingMetrics | None = None
    best_map50: float | None = None
    output_path: str | None = None
    error_message: str | None = None
    
    # Config
    config: TrainingConfig | None = None


class TrainingStartResponse(BaseModel):
    """Response from starting a training job."""
    
    ok: bool
    job_id: str
    message: str


class TrainingStopResponse(BaseModel):
    """Response from stopping a training job."""
    
    ok: bool
    job_id: str
    message: str


# ============ Training History ============

class TrainingJob(BaseModel):
    """Historical training job."""
    
    job_id: str
    dataset: str
    status: str
    started_at: str
    finished_at: str | None = None
    epochs_completed: int = 0
    best_map50: float | None = None
    output_bundle: str | None = None


class TrainingHistoryResponse(BaseModel):
    """List of historical training jobs."""
    
    jobs: list[TrainingJob]


# ============ Logs ============

class TrainingLogsResponse(BaseModel):
    """Training logs."""
    
    job_id: str
    logs: list[str]
    total_lines: int


# ============ Export ============

class ExportRequest(BaseModel):
    """Request to export a trained model."""
    
    model_path: str = Field(..., description="Path to trained .pt model")
    format: Literal["onnx", "openvino"] = Field(default="onnx", description="Export format")
    bundle_name: str = Field(..., description="Output bundle name")
    bundle_version: str = Field(default="v1", description="Output bundle version")
    img_size: int = Field(default=640, description="Image size for export")
    opset: int = Field(default=17, description="ONNX opset version")


class ExportResponse(BaseModel):
    """Response from model export."""
    
    ok: bool
    format: str
    bundle_path: str
    files: list[str]
