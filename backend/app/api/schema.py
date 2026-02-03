from __future__ import annotations

from pydantic import BaseModel, Field


class Box(BaseModel):
    x1: float = Field(..., description="Left (pixels, original image)")
    y1: float = Field(..., description="Top (pixels, original image)")
    x2: float = Field(..., description="Right (pixels, original image)")
    y2: float = Field(..., description="Bottom (pixels, original image)")


class Detection(BaseModel):
    class_id: int
    label: str
    score: float
    box: Box


class InferResponse(BaseModel):
    model_path: str | None
    image_width: int
    image_height: int
    detections: list[Detection]
    filter_applied: str | None = None


class ModelInfo(BaseModel):
    configured_model_path: str | None
    loaded: bool
    detail: str | None = None


class SettingsInfo(BaseModel):
    # High-signal config that impacts the demo UI behavior.
    demo_input_dir: str
    save_uploads: bool
    save_uploads_subdir: str
    demo_allow_mutations: bool
    allow_runtime_settings: bool
    # File counts (added for Settings UI)
    input_file_count: int | None = None
    uploads_file_count: int | None = None
    total_input_size_bytes: int | None = None


class SettingsUpdate(BaseModel):
    # All fields optional; only provided fields are applied.
    save_uploads: bool | None = None
    save_uploads_subdir: str | None = None
    demo_allow_mutations: bool | None = None


class BundleInfo(BaseModel):
    """Info about a model bundle in the registry."""

    name: str
    version: str
    path: str
    input_size: list[int] | None = None
    export_info: dict | None = None
    is_active: bool = False


class RegistryResponse(BaseModel):
    """Response from the model registry."""

    models_dir: str
    bundles: list[BundleInfo]
    active_model_path: str | None = None


# ============ P8: Filters ============

class FilterConfig(BaseModel):
    """Configuration for a detection filter."""
    
    name: str = Field(..., description="Filter name (e.g., 'buses_only')")
    enabled: bool = True
    include_classes: list[str] = Field(
        default_factory=list,
        description="Classes to include (empty = all)"
    )
    exclude_classes: list[str] = Field(
        default_factory=list,
        description="Classes to exclude"
    )
    min_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold"
    )


class FilterListResponse(BaseModel):
    """List of available filters."""
    
    filters: list[FilterConfig]
    active_filter: str | None = None


class FilterCreateRequest(BaseModel):
    """Request to create/update a filter."""
    
    name: str
    include_classes: list[str] = Field(default_factory=list)
    exclude_classes: list[str] = Field(default_factory=list)
    min_confidence: float = 0.5


# ============ P8: Watcher Status ============

class WatcherStatus(BaseModel):
    """Status of the folder watcher."""
    
    enabled: bool
    input_dir: str
    output_dir: str
    processed_dir: str | None = None
    mode: str = "json"  # json, move, both
    pending_files: int = 0
    processed_today: int = 0
    last_processed: str | None = None


# ============ P8: Model Upload ============

class ModelUploadResponse(BaseModel):
    """Response from model upload."""
    
    ok: bool
    name: str
    version: str
    path: str
    labels_count: int

