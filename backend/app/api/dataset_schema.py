"""Pydantic schemas for Dataset Management API (P10)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ============ Dataset ============

class DatasetCreate(BaseModel):
    """Request to create a new dataset."""
    
    name: str = Field(..., description="Dataset name (alphanumeric + underscore)")
    classes: list[str] = Field(default_factory=list, description="Initial class names")
    description: str | None = None


class DatasetInfo(BaseModel):
    """Information about a dataset."""
    
    name: str
    path: str
    classes: list[str]
    description: str | None = None
    created_at: str | None = None
    image_count: int = 0
    train_count: int = 0
    val_count: int = 0
    annotated_count: int = 0


class DatasetListResponse(BaseModel):
    """List of datasets."""
    
    datasets_dir: str
    datasets: list[DatasetInfo]


# ============ Images ============

class ImageInfo(BaseModel):
    """Information about an image in a dataset."""
    
    id: str = Field(..., description="Image ID (filename without extension)")
    filename: str
    path: str
    split: Literal["train", "val"] = "train"
    width: int | None = None
    height: int | None = None
    has_annotations: bool = False
    annotation_count: int = 0


class ImageListResponse(BaseModel):
    """List of images in a dataset."""
    
    dataset: str
    split: str | None = None
    images: list[ImageInfo]
    total: int


class ImageUploadResponse(BaseModel):
    """Response from image upload."""
    
    ok: bool
    dataset: str
    uploaded: list[str]
    failed: list[str] = Field(default_factory=list)
    total_uploaded: int


# ============ Annotations ============

class Annotation(BaseModel):
    """A single YOLO annotation (normalized coordinates)."""
    
    class_id: int = Field(..., ge=0, description="Class index")
    x_center: float = Field(..., ge=0.0, le=1.0, description="Center X (normalized)")
    y_center: float = Field(..., ge=0.0, le=1.0, description="Center Y (normalized)")
    width: float = Field(..., ge=0.0, le=1.0, description="Width (normalized)")
    height: float = Field(..., ge=0.0, le=1.0, description="Height (normalized)")


class AnnotationList(BaseModel):
    """Annotations for an image."""
    
    image_id: str
    annotations: list[Annotation]
    class_names: list[str] | None = None


class AnnotationUpdate(BaseModel):
    """Request to update annotations for an image."""
    
    annotations: list[Annotation]


# ============ Classes ============

class ClassListResponse(BaseModel):
    """List of classes in a dataset."""
    
    dataset: str
    classes: list[str]


class ClassUpdateRequest(BaseModel):
    """Request to update class names."""
    
    classes: list[str]


# ============ Export ============

class DatasetExportResponse(BaseModel):
    """Response from dataset export."""
    
    ok: bool
    dataset: str
    format: str
    path: str
    size_bytes: int
