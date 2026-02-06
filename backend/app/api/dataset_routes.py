"""Dataset Management API routes (P10)."""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from PIL import Image

from app.api.dataset_schema import (
    Annotation,
    AnnotationList,
    AnnotationUpdate,
    ClassListResponse,
    ClassUpdateRequest,
    DatasetCreate,
    DatasetExportResponse,
    DatasetInfo,
    DatasetListResponse,
    ImageInfo,
    ImageListResponse,
    ImageUploadResponse,
)

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


# ============ Helpers ============

def _datasets_dir() -> Path:
    """Return the datasets directory."""
    env_path = os.getenv("VISION_DATASETS_DIR")
    if env_path:
        return Path(env_path).resolve()
    
    # Default: /datasets in Docker, or repo-relative for local dev
    docker_path = Path("/datasets")
    if docker_path.exists():
        return docker_path
    
    # Local dev fallback
    return Path(__file__).parent.parent.parent.parent / "datasets"


def _dataset_path(name: str) -> Path:
    """Get path to a specific dataset."""
    return _datasets_dir() / name


def _safe_name(name: str) -> str:
    """Sanitize dataset/image name."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)


def _is_image_file(path: Path) -> bool:
    """Check if file is a supported image."""
    return path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


def _load_dataset_meta(dataset_path: Path) -> dict:
    """Load dataset metadata."""
    meta_path = dataset_path / "meta.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    return {}


def _save_dataset_meta(dataset_path: Path, meta: dict) -> None:
    """Save dataset metadata."""
    meta_path = dataset_path / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def _load_classes(dataset_path: Path) -> list[str]:
    """Load class names from dataset."""
    # First try classes.txt
    classes_path = dataset_path / "classes.txt"
    if classes_path.exists():
        return [l.strip() for l in classes_path.read_text(encoding="utf-8").strip().split("\n") if l.strip()]
    
    # Fallback to meta.json
    meta = _load_dataset_meta(dataset_path)
    return meta.get("classes", [])


def _save_classes(dataset_path: Path, classes: list[str]) -> None:
    """Save class names to dataset."""
    classes_path = dataset_path / "classes.txt"
    classes_path.write_text("\n".join(classes) + "\n", encoding="utf-8")
    
    # Also update meta.json
    meta = _load_dataset_meta(dataset_path)
    meta["classes"] = classes
    _save_dataset_meta(dataset_path, meta)


def _count_images(images_dir: Path, split: str | None = None) -> int:
    """Count images in a directory."""
    if not images_dir.exists():
        return 0
    
    if split:
        split_dir = images_dir / split
        if not split_dir.exists():
            return 0
        return sum(1 for f in split_dir.iterdir() if f.is_file() and _is_image_file(f))
    
    # Count all splits
    count = 0
    for split_dir in images_dir.iterdir():
        if split_dir.is_dir():
            count += sum(1 for f in split_dir.iterdir() if f.is_file() and _is_image_file(f))
    return count


def _count_annotated(dataset_path: Path) -> int:
    """Count images with annotations."""
    labels_dir = dataset_path / "labels"
    if not labels_dir.exists():
        return 0
    
    count = 0
    for split_dir in labels_dir.iterdir():
        if split_dir.is_dir():
            count += sum(1 for f in split_dir.iterdir() if f.suffix == ".txt" and f.stat().st_size > 0)
    return count


def _get_dataset_info(name: str, dataset_path: Path) -> DatasetInfo:
    """Build DatasetInfo for a dataset."""
    meta = _load_dataset_meta(dataset_path)
    classes = _load_classes(dataset_path)
    images_dir = dataset_path / "images"
    
    return DatasetInfo(
        name=name,
        path=str(dataset_path),
        classes=classes,
        description=meta.get("description"),
        created_at=meta.get("created_at"),
        image_count=_count_images(images_dir),
        train_count=_count_images(images_dir, "train"),
        val_count=_count_images(images_dir, "val"),
        annotated_count=_count_annotated(dataset_path),
    )


# ============ Dataset CRUD ============

@router.get("", response_model=DatasetListResponse)
def list_datasets() -> DatasetListResponse:
    """List all datasets."""
    datasets_dir = _datasets_dir()
    datasets_dir.mkdir(parents=True, exist_ok=True)
    
    datasets = []
    for item in sorted(datasets_dir.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            try:
                datasets.append(_get_dataset_info(item.name, item))
            except Exception:
                continue
    
    return DatasetListResponse(
        datasets_dir=str(datasets_dir),
        datasets=datasets,
    )


@router.post("", response_model=DatasetInfo)
def create_dataset(req: DatasetCreate) -> DatasetInfo:
    """Create a new dataset."""
    name = _safe_name(req.name)
    if not name:
        raise HTTPException(400, "Invalid dataset name")
    
    dataset_path = _dataset_path(name)
    if dataset_path.exists():
        raise HTTPException(409, f"Dataset '{name}' already exists")
    
    # Create directory structure
    dataset_path.mkdir(parents=True)
    (dataset_path / "images" / "train").mkdir(parents=True)
    (dataset_path / "images" / "val").mkdir(parents=True)
    (dataset_path / "labels" / "train").mkdir(parents=True)
    (dataset_path / "labels" / "val").mkdir(parents=True)
    
    # Save metadata
    meta = {
        "created_at": datetime.utcnow().isoformat(),
        "description": req.description,
        "classes": req.classes,
    }
    _save_dataset_meta(dataset_path, meta)
    
    # Save classes
    if req.classes:
        _save_classes(dataset_path, req.classes)
    
    # Create dataset.yaml for YOLO training
    yaml_content = f"""# Dataset config for YOLO training
path: {dataset_path}
train: images/train
val: images/val

names:
"""
    for i, cls in enumerate(req.classes):
        yaml_content += f"  {i}: {cls}\n"
    
    (dataset_path / "dataset.yaml").write_text(yaml_content, encoding="utf-8")
    
    return _get_dataset_info(name, dataset_path)


@router.get("/{name}", response_model=DatasetInfo)
def get_dataset(name: str) -> DatasetInfo:
    """Get dataset information."""
    dataset_path = _dataset_path(name)
    if not dataset_path.exists():
        raise HTTPException(404, f"Dataset '{name}' not found")
    
    return _get_dataset_info(name, dataset_path)


@router.delete("/{name}")
def delete_dataset(name: str) -> dict:
    """Delete a dataset."""
    dataset_path = _dataset_path(name)
    if not dataset_path.exists():
        raise HTTPException(404, f"Dataset '{name}' not found")
    
    shutil.rmtree(dataset_path)
    return {"ok": True, "deleted": name}


# ============ Images ============

@router.get("/{name}/images", response_model=ImageListResponse)
def list_images(
    name: str,
    split: Literal["train", "val"] | None = Query(None, description="Filter by split"),
) -> ImageListResponse:
    """List images in a dataset."""
    dataset_path = _dataset_path(name)
    if not dataset_path.exists():
        raise HTTPException(404, f"Dataset '{name}' not found")
    
    images_dir = dataset_path / "images"
    labels_dir = dataset_path / "labels"
    
    images = []
    splits = [split] if split else ["train", "val"]
    
    for s in splits:
        split_images = images_dir / s
        split_labels = labels_dir / s
        
        if not split_images.exists():
            continue
        
        for img_path in sorted(split_images.iterdir()):
            if not img_path.is_file() or not _is_image_file(img_path):
                continue
            
            img_id = img_path.stem
            label_path = split_labels / f"{img_id}.txt"
            
            # Get image dimensions
            width, height = None, None
            try:
                with Image.open(img_path) as img:
                    width, height = img.size
            except Exception:
                pass
            
            # Count annotations
            annotation_count = 0
            has_annotations = False
            if label_path.exists():
                content = label_path.read_text(encoding="utf-8").strip()
                if content:
                    has_annotations = True
                    annotation_count = len(content.split("\n"))
            
            images.append(ImageInfo(
                id=img_id,
                filename=img_path.name,
                path=str(img_path),
                split=s,
                width=width,
                height=height,
                has_annotations=has_annotations,
                annotation_count=annotation_count,
            ))
    
    return ImageListResponse(
        dataset=name,
        split=split,
        images=images,
        total=len(images),
    )


@router.post("/{name}/images", response_model=ImageUploadResponse)
async def upload_images(
    name: str,
    images: list[UploadFile] = File(...),
    split: Literal["train", "val"] = Query("train", description="Target split"),
) -> ImageUploadResponse:
    """Upload images to a dataset."""
    dataset_path = _dataset_path(name)
    if not dataset_path.exists():
        raise HTTPException(404, f"Dataset '{name}' not found")
    
    target_dir = dataset_path / "images" / split
    target_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded = []
    failed = []
    
    for upload in images:
        try:
            raw = await upload.read()
            
            # Validate it's an image
            try:
                img = Image.open(io.BytesIO(raw))
                img.verify()
            except Exception:
                failed.append(upload.filename or "unknown")
                continue
            
            # Save with safe filename
            safe_filename = _safe_name(Path(upload.filename or "image").stem)
            ext = Path(upload.filename or ".jpg").suffix.lower()
            if ext not in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}:
                ext = ".jpg"
            
            final_name = f"{safe_filename}{ext}"
            target_path = target_dir / final_name
            
            # Handle duplicates
            counter = 1
            while target_path.exists():
                final_name = f"{safe_filename}_{counter}{ext}"
                target_path = target_dir / final_name
                counter += 1
            
            target_path.write_bytes(raw)
            uploaded.append(final_name)
            
        except Exception:
            failed.append(upload.filename or "unknown")
    
    return ImageUploadResponse(
        ok=len(uploaded) > 0,
        dataset=name,
        uploaded=uploaded,
        failed=failed,
        total_uploaded=len(uploaded),
    )


@router.get("/{name}/images/{image_id}/file")
def get_image_file(
    name: str,
    image_id: str,
    split: Literal["train", "val"] = Query("train"),
) -> StreamingResponse:
    """Get an image file."""
    dataset_path = _dataset_path(name)
    if not dataset_path.exists():
        raise HTTPException(404, f"Dataset '{name}' not found")
    
    images_dir = dataset_path / "images" / split
    
    # Find image with any extension
    for ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"]:
        img_path = images_dir / f"{image_id}{ext}"
        if img_path.exists():
            media_type = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
                ".bmp": "image/bmp",
                ".gif": "image/gif",
            }.get(ext, "image/jpeg")
            
            return StreamingResponse(
                io.BytesIO(img_path.read_bytes()),
                media_type=media_type,
            )
    
    raise HTTPException(404, f"Image '{image_id}' not found in {split}")


@router.delete("/{name}/images/{image_id}")
def delete_image(
    name: str,
    image_id: str,
    split: Literal["train", "val"] = Query("train"),
) -> dict:
    """Delete an image and its annotations."""
    dataset_path = _dataset_path(name)
    if not dataset_path.exists():
        raise HTTPException(404, f"Dataset '{name}' not found")
    
    images_dir = dataset_path / "images" / split
    labels_dir = dataset_path / "labels" / split
    
    deleted_image = False
    deleted_label = False
    
    # Delete image
    for ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"]:
        img_path = images_dir / f"{image_id}{ext}"
        if img_path.exists():
            img_path.unlink()
            deleted_image = True
            break
    
    # Delete label
    label_path = labels_dir / f"{image_id}.txt"
    if label_path.exists():
        label_path.unlink()
        deleted_label = True
    
    if not deleted_image:
        raise HTTPException(404, f"Image '{image_id}' not found")
    
    return {"ok": True, "deleted_image": image_id, "deleted_label": deleted_label}


# ============ Annotations ============

@router.get("/{name}/images/{image_id}/annotations", response_model=AnnotationList)
def get_annotations(
    name: str,
    image_id: str,
    split: Literal["train", "val"] = Query("train"),
) -> AnnotationList:
    """Get annotations for an image."""
    dataset_path = _dataset_path(name)
    if not dataset_path.exists():
        raise HTTPException(404, f"Dataset '{name}' not found")
    
    label_path = dataset_path / "labels" / split / f"{image_id}.txt"
    classes = _load_classes(dataset_path)
    
    annotations = []
    if label_path.exists():
        content = label_path.read_text(encoding="utf-8").strip()
        for line in content.split("\n"):
            if not line.strip():
                continue
            parts = line.strip().split()
            if len(parts) >= 5:
                annotations.append(Annotation(
                    class_id=int(parts[0]),
                    x_center=float(parts[1]),
                    y_center=float(parts[2]),
                    width=float(parts[3]),
                    height=float(parts[4]),
                ))
    
    return AnnotationList(
        image_id=image_id,
        annotations=annotations,
        class_names=classes,
    )


@router.put("/{name}/images/{image_id}/annotations", response_model=AnnotationList)
def update_annotations(
    name: str,
    image_id: str,
    req: AnnotationUpdate,
    split: Literal["train", "val"] = Query("train"),
) -> AnnotationList:
    """Update annotations for an image."""
    dataset_path = _dataset_path(name)
    if not dataset_path.exists():
        raise HTTPException(404, f"Dataset '{name}' not found")
    
    labels_dir = dataset_path / "labels" / split
    labels_dir.mkdir(parents=True, exist_ok=True)
    
    label_path = labels_dir / f"{image_id}.txt"
    
    # Convert to YOLO format
    lines = []
    for ann in req.annotations:
        lines.append(f"{ann.class_id} {ann.x_center:.6f} {ann.y_center:.6f} {ann.width:.6f} {ann.height:.6f}")
    
    label_path.write_text("\n".join(lines) + "\n" if lines else "", encoding="utf-8")
    
    return get_annotations(name, image_id, split)


# ============ Classes ============

@router.get("/{name}/classes", response_model=ClassListResponse)
def get_classes(name: str) -> ClassListResponse:
    """Get class names for a dataset."""
    dataset_path = _dataset_path(name)
    if not dataset_path.exists():
        raise HTTPException(404, f"Dataset '{name}' not found")
    
    return ClassListResponse(
        dataset=name,
        classes=_load_classes(dataset_path),
    )


@router.put("/{name}/classes", response_model=ClassListResponse)
def update_classes(name: str, req: ClassUpdateRequest) -> ClassListResponse:
    """Update class names for a dataset."""
    dataset_path = _dataset_path(name)
    if not dataset_path.exists():
        raise HTTPException(404, f"Dataset '{name}' not found")
    
    _save_classes(dataset_path, req.classes)
    
    # Update dataset.yaml
    yaml_path = dataset_path / "dataset.yaml"
    yaml_content = f"""# Dataset config for YOLO training
path: {dataset_path}
train: images/train
val: images/val

names:
"""
    for i, cls in enumerate(req.classes):
        yaml_content += f"  {i}: {cls}\n"
    
    yaml_path.write_text(yaml_content, encoding="utf-8")
    
    return ClassListResponse(dataset=name, classes=req.classes)


# ============ Export ============

@router.post("/{name}/export", response_model=DatasetExportResponse)
def export_dataset(
    name: str,
    format: Literal["yolo", "zip"] = Query("zip", description="Export format"),
) -> StreamingResponse:
    """Export dataset as a zip file."""
    dataset_path = _dataset_path(name)
    if not dataset_path.exists():
        raise HTTPException(404, f"Dataset '{name}' not found")
    
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in dataset_path.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(dataset_path)
                zf.write(file_path, arcname=arcname)
    
    buf.seek(0)
    
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={name}_dataset.zip",
        },
    )
