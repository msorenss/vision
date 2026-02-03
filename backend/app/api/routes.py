from __future__ import annotations

import io
import json
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from PIL import Image, ImageOps

from app.api.schema import (
    BundleInfo,
    FilterConfig,
    FilterCreateRequest,
    FilterListResponse,
    InferResponse,
    ModelInfo,
    ModelUploadResponse,
    RegistryResponse,
    SettingsInfo,
    SettingsUpdate,
    WatcherStatus,
)
from app.inference.engine import get_engine, reset_engine

router = APIRouter()


@router.get("/")
def root() -> dict:
    return {
        "ok": True,
        "message": "Vision Runner API",
        "health": "/health",
        "docs": "/docs",
    }


@router.get("/favicon.ico")
def favicon() -> Response:
    # Avoid noisy 404s from browsers.
    return Response(status_code=204)


@router.get("/health")
def health() -> dict:
    engine = get_engine()
    return {
        "ok": True,
        "model": {
            "configured_path": engine.configured_model_path,
            "loaded": engine.loaded,
            "detail": engine.detail,
        },
    }


@router.get("/health/ready")
def health_ready() -> dict:
    """Readiness probe for k8s-style orchestration."""
    engine = get_engine()
    if not engine.loaded:
        raise HTTPException(
            status_code=503,
            detail=engine.detail or "Model not loaded",
        )
    return {"ready": True, "model_path": engine.configured_model_path}


def _demo_input_dir() -> Path:
    return Path(os.getenv("VISION_DEMO_INPUT", "/input")).resolve()


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _allow_runtime_settings() -> bool:
    return _truthy(os.getenv("VISION_ALLOW_RUNTIME_SETTINGS", "0"))


def _count_images(
    path: Path,
    exclude_subdir: str | None = None,
) -> tuple[int, int]:
    """Return (file_count, total_bytes) for image files in path.

    If exclude_subdir is provided, skip files whose relative path
    contains that subdirectory name.
    """
    count = 0
    total_bytes = 0
    if not path.exists():
        return (0, 0)
    for f in path.rglob("*"):
        if not f.is_file():
            continue
        if not _is_image_suffix(f):
            continue
        if exclude_subdir:
            try:
                rel = f.relative_to(path)
                if rel.parts and rel.parts[0] == exclude_subdir:
                    continue
            except ValueError:
                pass
        try:
            total_bytes += f.stat().st_size
        except OSError:
            pass
        count += 1
    return (count, total_bytes)


def _settings_info() -> SettingsInfo:
    base = _demo_input_dir()
    uploads_subdir = os.getenv("VISION_SAVE_UPLOADS_SUBDIR", "_uploads")

    # Count input files (excluding uploads subfolder)
    input_count, input_bytes = _count_images(base, exclude_subdir=uploads_subdir)

    # Count uploads files
    uploads_dir = base / uploads_subdir
    uploads_count, uploads_bytes = _count_images(uploads_dir)

    return SettingsInfo(
        demo_input_dir=str(base),
        save_uploads=_truthy(os.getenv("VISION_SAVE_UPLOADS", "0")),
        save_uploads_subdir=uploads_subdir,
        demo_allow_mutations=_truthy(
            os.getenv("VISION_DEMO_ALLOW_MUTATIONS", "0")
        ),
        allow_runtime_settings=_allow_runtime_settings(),
        input_file_count=input_count,
        uploads_file_count=uploads_count,
        total_input_size_bytes=input_bytes + uploads_bytes,
    )


def _safe_filename(name: str) -> str:
    # Keep only a conservative set of characters.
    base = Path(name).name
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    base = base.strip("._")
    return base or "upload"


def _maybe_persist_upload(raw: bytes, original_name: str | None) -> None:
    if not _truthy(os.getenv("VISION_SAVE_UPLOADS", "0")):
        return

    base = _demo_input_dir()
    subdir = os.getenv("VISION_SAVE_UPLOADS_SUBDIR", "_uploads")
    out_dir = (base / subdir).resolve()

    # Prevent path traversal via subdir.
    try:
        out_dir.relative_to(base)
    except ValueError:
        out_dir = (base / "_uploads").resolve()

    out_dir.mkdir(parents=True, exist_ok=True)

    safe = _safe_filename(original_name or "upload")
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    out_path = out_dir / f"{ts}_{safe}"
    out_path.write_bytes(raw)


def _resolve_uploads_dir(base: Path) -> Path:
    subdir = os.getenv("VISION_SAVE_UPLOADS_SUBDIR", "_uploads")
    out_dir = (base / subdir).resolve()
    try:
        out_dir.relative_to(base)
    except ValueError:
        out_dir = (base / "_uploads").resolve()
    return out_dir


def _clear_dir_tree(target: Path) -> tuple[int, int]:
    deleted_files = 0
    deleted_dirs = 0

    if not target.exists():
        return (0, 0)

    # Delete deepest paths first.
    items = sorted(
        target.rglob("*"),
        key=lambda x: len(str(x)),
        reverse=True,
    )
    for p in items:
        try:
            if p.is_file():
                p.unlink(missing_ok=True)
                deleted_files += 1
            elif p.is_dir():
                # Remove empty dirs; ignore non-empty.
                p.rmdir()
                deleted_dirs += 1
        except Exception:
            continue

    return (deleted_files, deleted_dirs)


def _is_image_suffix(path: Path) -> bool:
    return path.suffix.lower() in {
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".webp",
        ".heic",
        ".heif",
    }


@router.get("/api/v1/demo/files")
def demo_files() -> dict:
    """List images available in the input folder (Runner volume).

    Useful for quick smoke tests without uploading.
    """

    base = _demo_input_dir()
    if not base.exists():
        return {"input_dir": str(base), "files": []}

    files: list[str] = []
    for p in base.rglob("*"):
        if not p.is_file():
            continue
        if not _is_image_suffix(p):
            continue
        files.append(str(p.relative_to(base)).replace("\\", "/"))
    files.sort()
    return {"input_dir": str(base), "files": files}


@router.post("/api/v1/demo/clear")
def demo_clear(
    scope: str = Query(
        default="uploads",
        description="What to clear: uploads (default) or all",
    ),
) -> dict:
    """Delete files under the demo input folder.

    Safety:
    - Disabled by default. Enable by setting VISION_DEMO_ALLOW_MUTATIONS=1.
    - Default scope clears only the uploads subfolder.
    """

    if not _truthy(os.getenv("VISION_DEMO_ALLOW_MUTATIONS", "0")):
        raise HTTPException(
            status_code=403,
            detail=(
                "Demo mutations are disabled. "
                "Set VISION_DEMO_ALLOW_MUTATIONS=1 to enable "
                "/api/v1/demo/clear."
            ),
        )

    base = _demo_input_dir()
    if not base.exists():
        return {
            "input_dir": str(base),
            "scope": scope,
            "deleted_files": 0,
            "deleted_dirs": 0,
        }

    if scope not in {"uploads", "all"}:
        raise HTTPException(
            status_code=400,
            detail="scope must be 'uploads' or 'all'",
        )

    if scope == "uploads":
        target = _resolve_uploads_dir(base)
    else:
        target = base

    # Prevent path traversal / accidental deletion outside base.
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid target path",
        ) from exc

    deleted_files, deleted_dirs = _clear_dir_tree(target)
    return {
        "input_dir": str(base),
        "scope": scope,
        "target": str(target),
        "deleted_files": deleted_files,
        "deleted_dirs": deleted_dirs,
    }


@router.get("/api/v1/demo/infer", response_model=InferResponse)
def demo_infer(name: str) -> InferResponse:
    """Run inference on a file already present in the input folder.

    Example: GET /api/v1/demo/infer?name=test.jpg
    """

    base = _demo_input_dir()
    candidate = (base / name).resolve()

    # Prevent path traversal.
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid file path",
        ) from exc

    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if not _is_image_suffix(candidate):
        raise HTTPException(status_code=415, detail="File is not an image")

    try:
        pil = ImageOps.exif_transpose(Image.open(candidate)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image: {exc}",
        ) from exc

    engine = get_engine()
    if not engine.configured_model_path:
        raise HTTPException(
            status_code=503,
            detail=(
                "No model configured. Set VISION_MODEL_PATH to a YOLO ONNX "
                "model bundle (model.onnx + labels.txt + meta.json)."
            ),
        )

    detections = engine.predict(pil)
    return InferResponse(
        model_path=engine.configured_model_path,
        image_width=pil.width,
        image_height=pil.height,
        detections=detections,
    )


@router.get("/api/v1/demo/image")
def demo_image(name: str) -> FileResponse:
    """Serve an image from the input folder so the UI can preview it."""

    base = _demo_input_dir()
    candidate = (base / name).resolve()

    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid file path",
        ) from exc

    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if not _is_image_suffix(candidate):
        raise HTTPException(status_code=415, detail="File is not an image")

    return FileResponse(path=str(candidate))


@router.get("/api/v1/models", response_model=ModelInfo)
def models() -> ModelInfo:
    engine = get_engine()
    return ModelInfo(
        configured_model_path=engine.configured_model_path,
        loaded=engine.loaded,
        detail=engine.detail,
    )


@router.get("/api/v1/settings", response_model=SettingsInfo)
def get_settings() -> SettingsInfo:
    return _settings_info()


@router.post("/api/v1/settings", response_model=SettingsInfo)
def update_settings(update: SettingsUpdate) -> SettingsInfo:
    if not _allow_runtime_settings():
        raise HTTPException(
            status_code=403,
            detail=(
                "Runtime settings are disabled. "
                "Set VISION_ALLOW_RUNTIME_SETTINGS=1 to enable "
                "/api/v1/settings updates."
            ),
        )

    if update.save_uploads is not None:
        os.environ["VISION_SAVE_UPLOADS"] = "1" if update.save_uploads else "0"

    if update.save_uploads_subdir is not None:
        val = update.save_uploads_subdir.strip() or "_uploads"
        os.environ["VISION_SAVE_UPLOADS_SUBDIR"] = val

    if update.demo_allow_mutations is not None:
        os.environ["VISION_DEMO_ALLOW_MUTATIONS"] = (
            "1" if update.demo_allow_mutations else "0"
        )

    return _settings_info()


@router.post("/api/v1/models/reload", response_model=ModelInfo)
def reload_model() -> ModelInfo:
    """Reload engine from environment variables (VISION_MODEL_PATH)."""
    reset_engine()
    return models()


def _models_dir() -> Path:
    """Return the models directory.
    
    Uses VISION_MODELS_DIR env var if set, otherwise /models (Docker) 
    or repo-relative path (local dev).
    """
    env_path = os.getenv("VISION_MODELS_DIR")
    if env_path:
        return Path(env_path).resolve()
    
    # Docker typically mounts to /models
    docker_path = Path("/models")
    if docker_path.exists():
        return docker_path
    
    # Fallback: repo-relative for local dev
    here = Path(__file__).resolve()
    return here.parents[2] / "models"


def _scan_bundles() -> list[BundleInfo]:
    """Scan models/ for valid bundles."""
    import json

    models_dir = _models_dir()
    if not models_dir.exists():
        return []

    engine = get_engine()
    active_path = engine.configured_model_path

    bundles: list[BundleInfo] = []
    for name_dir in models_dir.iterdir():
        if not name_dir.is_dir():
            continue
        for version_dir in name_dir.iterdir():
            if not version_dir.is_dir():
                continue
            model_file = version_dir / "model.onnx"
            meta_file = version_dir / "meta.json"
            if not model_file.exists():
                continue

            input_size = None
            export_info = None
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    input_size = meta.get("input_size")
                    export_info = meta.get("export")
                except Exception:
                    pass

            is_active = active_path and str(model_file) == active_path
            bundles.append(
                BundleInfo(
                    name=name_dir.name,
                    version=version_dir.name,
                    path=str(version_dir),
                    input_size=input_size,
                    export_info=export_info,
                    is_active=is_active,
                )
            )

    return sorted(bundles, key=lambda b: (b.name, b.version))


@router.get("/api/v1/registry", response_model=RegistryResponse)
def list_registry() -> RegistryResponse:
    """List all model bundles in the registry."""
    engine = get_engine()
    return RegistryResponse(
        models_dir=str(_models_dir()),
        bundles=_scan_bundles(),
        active_model_path=engine.configured_model_path,
    )


@router.post("/api/v1/registry/activate", response_model=ModelInfo)
def activate_model(
    name: str = Query(..., description="Bundle name (e.g. 'demo')"),
    version: str = Query(..., description="Bundle version (e.g. 'v1')"),
) -> ModelInfo:
    """Activate a specific model bundle."""
    if not _allow_runtime_settings():
        raise HTTPException(
            status_code=403,
            detail=(
                "Runtime settings are disabled. "
                "Set VISION_ALLOW_RUNTIME_SETTINGS=1 to enable model switching."
            ),
        )

    bundle_dir = _models_dir() / name / version
    model_file = bundle_dir / "model.onnx"

    if not model_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Bundle not found: {name}/{version}",
        )

    os.environ["VISION_MODEL_PATH"] = str(model_file)
    reset_engine()
    return models()


@router.post("/api/v1/models/bundle/import")
async def import_model_bundle(
    bundle: UploadFile = File(...),
    name: str = Query(..., description="Bundle name"),
    version: str = Query(..., description="Bundle version"),
) -> dict:
    """Import a model bundle from a zip file."""
    if not _allow_runtime_settings():
        raise HTTPException(
            status_code=403,
            detail="Runtime settings are disabled.",
        )

    raw = await bundle.read()
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise HTTPException(400, "Invalid zip file") from exc

    # Validate contents
    names = zf.namelist()
    required = {"model.onnx", "labels.txt", "meta.json"}
    missing = required - set(names)
    if missing:
        raise HTTPException(
            400, f"Bundle missing required files: {', '.join(missing)}"
        )

    # Extract to models/<name>/<version>/
    bundle_dir = _models_dir() / name / version
    bundle_dir.mkdir(parents=True, exist_ok=True)
    zf.extractall(bundle_dir)

    return {
        "ok": True,
        "path": str(bundle_dir),
        "files": names,
    }


@router.get("/api/v1/models/bundle")
def download_model_bundle() -> StreamingResponse:
    """Download the currently configured model bundle as a zip.

    Intended for a Pi Runner to pull bundles from a Builder instance.
    """

    engine = get_engine()
    if not engine.configured_model_path:
        raise HTTPException(status_code=404, detail="No model configured")

    model_path = Path(engine.configured_model_path)
    bundle_dir = model_path.parent

    files = [
        bundle_dir / "model.onnx",
        bundle_dir / "labels.txt",
        bundle_dir / "meta.json",
    ]
    missing = [p.name for p in files if not p.exists()]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Bundle missing required files: {', '.join(missing)}",
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            zf.write(p, arcname=p.name)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=model-bundle.zip",
        },
    )


@router.post("/api/v1/infer", response_model=InferResponse)
async def infer(
    image: UploadFile | None = File(None),
    file: UploadFile | None = File(None),
) -> InferResponse:
    upload = image or file
    if upload is None:
        raise HTTPException(
            status_code=422,
            detail="Missing multipart file field 'image' (or legacy 'file')",
        )

    raw = await upload.read()

    # Check file size limit
    max_mb = float(os.getenv("VISION_MAX_UPLOAD_MB", "10"))
    max_bytes = int(max_mb * 1024 * 1024)
    if len(raw) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File too large: {len(raw) / (1024*1024):.1f} MB. "
                f"Maximum allowed: {max_mb} MB. "
                f"Set VISION_MAX_UPLOAD_MB to increase limit."
            ),
        )

    try:
        pil = ImageOps.exif_transpose(
            Image.open(io.BytesIO(raw))
        ).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=415,
            detail=f"Upload must be a supported image format: {exc}",
        ) from exc

    # Optional: persist uploads into the mounted /input folder so they can be
    # re-used via the demo endpoints.
    _maybe_persist_upload(raw, upload.filename)

    engine = get_engine()
    if not engine.configured_model_path:
        raise HTTPException(
            status_code=503,
            detail=(
                "No model configured. Set VISION_MODEL_PATH to a YOLO ONNX "
                "model bundle (model.onnx + labels.txt + meta.json)."
            ),
        )

    try:
        detections = engine.predict(pil)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return InferResponse(
        model_path=engine.configured_model_path,
        image_width=pil.width,
        image_height=pil.height,
        detections=detections,
    )


# ============ P8: Filters ============

def _filters_path() -> Path:
    """Return path to filters.json config file."""
    env_path = os.getenv("VISION_FILTERS_PATH")
    if env_path:
        return Path(env_path).resolve()
    
    # Check in app directory first
    app_dir = Path(__file__).parent.parent.parent
    candidate = app_dir / "filters.json"
    if candidate.exists():
        return candidate
    
    # Fallback to creating in models dir
    models_dir = _models_dir()
    return models_dir / "filters.json"


def _load_filters() -> dict[str, FilterConfig]:
    """Load filters from JSON file."""
    path = _filters_path()
    if not path.exists():
        return {"default": FilterConfig(
            name="default",
            enabled=True,
            include_classes=[],
            exclude_classes=[],
            min_confidence=0.5
        )}
    
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            name: FilterConfig(name=name, **cfg) if "name" not in cfg else FilterConfig(**cfg)
            for name, cfg in data.items()
        }
    except Exception:
        return {}


def _save_filters(filters: dict[str, FilterConfig]) -> None:
    """Save filters to JSON file."""
    path = _filters_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        name: {
            "name": f.name,
            "enabled": f.enabled,
            "include_classes": f.include_classes,
            "exclude_classes": f.exclude_classes,
            "min_confidence": f.min_confidence,
        }
        for name, f in filters.items()
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _apply_filter(
    detections: list,
    filter_config: FilterConfig
) -> list:
    """Apply filter to detection list."""
    if not filter_config.enabled:
        return detections
    
    result = []
    for det in detections:
        # Check confidence threshold
        if det.score < filter_config.min_confidence:
            continue
        
        # Check include list (empty = include all)
        if filter_config.include_classes:
            if det.label.lower() not in [c.lower() for c in filter_config.include_classes]:
                continue
        
        # Check exclude list
        if filter_config.exclude_classes:
            if det.label.lower() in [c.lower() for c in filter_config.exclude_classes]:
                continue
        
        result.append(det)
    
    return result


@router.get("/api/v1/filters", response_model=FilterListResponse)
def list_filters() -> FilterListResponse:
    """List all available detection filters."""
    filters = _load_filters()
    return FilterListResponse(
        filters=list(filters.values()),
        active_filter=os.getenv("VISION_ACTIVE_FILTER"),
    )


@router.get("/api/v1/filters/{name}", response_model=FilterConfig)
def get_filter(name: str) -> FilterConfig:
    """Get a specific filter by name."""
    filters = _load_filters()
    if name not in filters:
        raise HTTPException(status_code=404, detail=f"Filter '{name}' not found")
    return filters[name]


@router.post("/api/v1/filters", response_model=FilterConfig)
def create_filter(req: FilterCreateRequest) -> FilterConfig:
    """Create or update a detection filter."""
    if not _allow_runtime_settings():
        raise HTTPException(
            status_code=403,
            detail="Runtime settings are disabled.",
        )
    
    filters = _load_filters()
    new_filter = FilterConfig(
        name=req.name,
        enabled=True,
        include_classes=req.include_classes,
        exclude_classes=req.exclude_classes,
        min_confidence=req.min_confidence,
    )
    filters[req.name] = new_filter
    _save_filters(filters)
    return new_filter


@router.delete("/api/v1/filters/{name}")
def delete_filter(name: str) -> dict:
    """Delete a filter."""
    if not _allow_runtime_settings():
        raise HTTPException(
            status_code=403,
            detail="Runtime settings are disabled.",
        )
    
    if name == "default":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the default filter.",
        )
    
    filters = _load_filters()
    if name not in filters:
        raise HTTPException(status_code=404, detail=f"Filter '{name}' not found")
    
    del filters[name]
    _save_filters(filters)
    return {"ok": True, "deleted": name}


# ============ P8: Watcher Status ============

@router.get("/api/v1/watcher/status", response_model=WatcherStatus)
def watcher_status() -> WatcherStatus:
    """Get the status of the folder watcher."""
    from app.watcher import load_watch_config
    
    cfg = load_watch_config()
    
    # Count pending files (images in input not yet processed)
    pending = 0
    if cfg.input_dir.exists():
        for f in cfg.input_dir.rglob("*"):
            if f.is_file() and _is_image_suffix(f):
                # Check if output JSON exists
                try:
                    rel = f.relative_to(cfg.input_dir)
                except ValueError:
                    continue
                out_json = cfg.output_dir / f"{rel.stem}.detections.json"
                if not out_json.exists():
                    pending += 1
    
    # Count processed today
    processed_today = 0
    today = datetime.now().date()
    if cfg.output_dir.exists():
        for f in cfg.output_dir.rglob("*.detections.json"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime.date() == today:
                    processed_today += 1
            except Exception:
                continue
    
    return WatcherStatus(
        enabled=cfg.enabled,
        input_dir=str(cfg.input_dir),
        output_dir=str(cfg.output_dir),
        processed_dir=str(cfg.processed_dir) if cfg.processed_dir else None,
        mode=cfg.mode if hasattr(cfg, 'mode') else "json",
        pending_files=pending,
        processed_today=processed_today,
    )


# ============ P8: Model Upload ============

@router.post("/api/v1/models/upload", response_model=ModelUploadResponse)
async def upload_model(
    model: UploadFile = File(..., description="ONNX model file"),
    labels: UploadFile = File(..., description="labels.txt file"),
    name: str = Query(..., description="Bundle name (e.g., 'custom')"),
    version: str = Query(default="v1", description="Bundle version"),
) -> ModelUploadResponse:
    """Upload a new model bundle (ONNX + labels)."""
    if not _allow_runtime_settings():
        raise HTTPException(
            status_code=403,
            detail="Runtime settings are disabled. Set VISION_ALLOW_RUNTIME_SETTINGS=1.",
        )
    
    # Validate name/version
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    safe_version = re.sub(r"[^a-zA-Z0-9_.-]", "_", version)
    
    if not safe_name or not safe_version:
        raise HTTPException(
            status_code=400,
            detail="Invalid name or version.",
        )
    
    # Check file sizes
    max_mb = float(os.getenv("VISION_MAX_MODEL_SIZE_MB", "500"))
    max_bytes = int(max_mb * 1024 * 1024)
    
    model_data = await model.read()
    if len(model_data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Model too large. Max: {max_mb} MB",
        )
    
    labels_data = await labels.read()
    labels_text = labels_data.decode("utf-8")
    labels_list = [l.strip() for l in labels_text.strip().split("\n") if l.strip()]
    
    if not labels_list:
        raise HTTPException(
            status_code=400,
            detail="labels.txt is empty or invalid.",
        )
    
    # Create bundle directory
    bundle_dir = _models_dir() / safe_name / safe_version
    bundle_dir.mkdir(parents=True, exist_ok=True)
    
    # Save files
    model_path = bundle_dir / "model.onnx"
    labels_path = bundle_dir / "labels.txt"
    meta_path = bundle_dir / "meta.json"
    
    model_path.write_bytes(model_data)
    labels_path.write_text(labels_text, encoding="utf-8")
    
    # Create meta.json
    meta = {
        "uploaded_at": datetime.utcnow().isoformat(),
        "labels_count": len(labels_list),
        "model_size_bytes": len(model_data),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    
    return ModelUploadResponse(
        ok=True,
        name=safe_name,
        version=safe_version,
        path=str(bundle_dir),
        labels_count=len(labels_list),
    )


# ============ P8: Infer with Filter ============

@router.post("/api/v1/infer/filtered", response_model=InferResponse)
async def infer_with_filter(
    image: UploadFile = File(...),
    filter_name: str = Query(default="default", description="Filter to apply"),
) -> InferResponse:
    """Run inference with a specific filter applied."""
    # Load filter
    filters = _load_filters()
    if filter_name not in filters:
        raise HTTPException(status_code=404, detail=f"Filter '{filter_name}' not found")
    
    filter_config = filters[filter_name]
    
    # Run normal inference
    raw = await image.read()
    
    try:
        pil = ImageOps.exif_transpose(
            Image.open(io.BytesIO(raw))
        ).convert("RGB")
    except Exception as exc:
        raise HTTPException(
            status_code=415,
            detail=f"Invalid image: {exc}",
        ) from exc
    
    engine = get_engine()
    if not engine.configured_model_path:
        raise HTTPException(
            status_code=503,
            detail="No model configured.",
        )
    
    detections = engine.predict(pil)
    
    # Apply filter
    filtered_detections = _apply_filter(detections, filter_config)
    
    return InferResponse(
        model_path=engine.configured_model_path,
        image_width=pil.width,
        image_height=pil.height,
        detections=filtered_detections,
        filter_applied=filter_name,
    )


@router.get("/api/v1/demo/infer/filtered", response_model=InferResponse)
def demo_infer_with_filter(
    name: str = Query(..., description="Demo file name"),
    filter_name: str = Query(default="default", description="Filter to apply"),
) -> InferResponse:
    """Run inference on a demo file with a specific filter applied."""
    filters = _load_filters()
    if filter_name not in filters:
        raise HTTPException(status_code=404, detail=f"Filter '{filter_name}' not found")
    
    base = _demo_input_dir()
    candidate = (base / name).resolve()

    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid file path") from exc

    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        pil = ImageOps.exif_transpose(Image.open(candidate)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image: {exc}") from exc

    engine = get_engine()
    if not engine.configured_model_path:
        raise HTTPException(status_code=503, detail="No model configured.")

    detections = engine.predict(pil)
    filtered_detections = _apply_filter(detections, filters[filter_name])
    
    return InferResponse(
        model_path=engine.configured_model_path,
        image_width=pil.width,
        image_height=pil.height,
        detections=filtered_detections,
        filter_applied=filter_name,
    )


@router.get("/api/v1/models/labels")
def get_model_labels() -> dict:
    """Get the labels from the currently loaded model."""
    engine = get_engine()
    if not engine.configured_model_path:
        raise HTTPException(status_code=503, detail="No model configured")
    
    model_path = Path(engine.configured_model_path)
    labels_path = model_path.parent / "labels.txt"
    
    if not labels_path.exists():
        raise HTTPException(status_code=404, detail="labels.txt not found")
    
    labels = [l.strip() for l in labels_path.read_text(encoding="utf-8").strip().split("\n")]
    return {
        "model_path": str(model_path),
        "labels": labels,
        "count": len(labels),
    }


# ============ Integrations ============

from app.api.schema import (
    IntegrationsStatus,
    IntegrationsUpdate,
    OpcUaStatus,
    MqttStatus,
    WebhookStatus,
)


def _get_integrations_status() -> IntegrationsStatus:
    """Get current status of all integrations."""
    # Check if libraries are available
    try:
        import aiomqtt
        mqtt_available = True
    except ImportError:
        mqtt_available = False
    
    try:
        from asyncua import Server
        opcua_available = True
    except ImportError:
        opcua_available = False
    
    # Get OPC UA status
    from app.integrations.opcua_server import server_instance
    opcua_enabled = os.getenv("VISION_OPCUA_ENABLE", "0") == "1"
    opcua_port = int(os.getenv("VISION_OPCUA_PORT", "4840"))
    opcua_endpoint = os.getenv(
        "VISION_OPCUA_ENDPOINT",
        f"opc.tcp://0.0.0.0:{opcua_port}/freeopcua/server/"
    )
    opcua_interval = int(os.getenv("VISION_OPCUA_UPDATE_INTERVAL_MS", "0"))
    
    opcua_status = OpcUaStatus(
        available=opcua_available,
        enabled=opcua_enabled,
        running=server_instance.running,
        endpoint=opcua_endpoint if opcua_enabled else None,
        port=opcua_port,
        namespace="http://volvocars.com/vision",
        update_interval_ms=opcua_interval,
    )
    
    # Get MQTT status
    mqtt_broker = os.getenv("VISION_MQTT_BROKER")
    mqtt_port = int(os.getenv("VISION_MQTT_PORT", "1883"))
    mqtt_topic = os.getenv("VISION_MQTT_TOPIC", "vision/results")
    mqtt_username = os.getenv("VISION_MQTT_USERNAME")
    
    mqtt_status = MqttStatus(
        available=mqtt_available,
        configured=bool(mqtt_broker),
        broker=mqtt_broker,
        port=mqtt_port,
        topic=mqtt_topic,
        username=mqtt_username,
    )
    
    # Get Webhook status
    webhook_url = os.getenv("VISION_WEBHOOK_URL")
    webhook_headers = os.getenv("VISION_WEBHOOK_HEADERS", "{}")
    has_custom_headers = webhook_headers != "{}" and bool(webhook_headers)
    
    webhook_status = WebhookStatus(
        configured=bool(webhook_url),
        url=webhook_url,
        has_custom_headers=has_custom_headers,
    )
    
    return IntegrationsStatus(
        opcua=opcua_status,
        mqtt=mqtt_status,
        webhook=webhook_status,
    )


@router.get("/api/v1/integrations", response_model=IntegrationsStatus)
def get_integrations() -> IntegrationsStatus:
    """Get status of all integrations (OPC UA, MQTT, Webhook)."""
    return _get_integrations_status()


@router.post("/api/v1/integrations", response_model=IntegrationsStatus)
async def update_integrations(update: IntegrationsUpdate) -> IntegrationsStatus:
    """Update integration settings at runtime."""
    if not _allow_runtime_settings():
        raise HTTPException(
            status_code=403,
            detail=(
                "Runtime settings are disabled. "
                "Set VISION_ALLOW_RUNTIME_SETTINGS=1 to enable "
                "/api/v1/integrations updates."
            ),
        )
    
    # Update OPC UA settings
    if update.opcua_enabled is not None:
        os.environ["VISION_OPCUA_ENABLE"] = "1" if update.opcua_enabled else "0"
        
        # Start or stop the OPC UA server
        from app.integrations.opcua_server import server_instance
        if update.opcua_enabled and not server_instance.running:
            await server_instance.start()
        elif not update.opcua_enabled and server_instance.running:
            await server_instance.stop()
    
    if update.opcua_port is not None:
        os.environ["VISION_OPCUA_PORT"] = str(update.opcua_port)
        # Rebuild the endpoint URL with new port
        os.environ["VISION_OPCUA_ENDPOINT"] = f"opc.tcp://0.0.0.0:{update.opcua_port}/freeopcua/server/"
    
    if update.opcua_update_interval_ms is not None:
        os.environ["VISION_OPCUA_UPDATE_INTERVAL_MS"] = str(update.opcua_update_interval_ms)
    
    # Update MQTT settings
    if update.mqtt_broker is not None:
        os.environ["VISION_MQTT_BROKER"] = update.mqtt_broker
    
    if update.mqtt_port is not None:
        os.environ["VISION_MQTT_PORT"] = str(update.mqtt_port)
    
    if update.mqtt_topic is not None:
        os.environ["VISION_MQTT_TOPIC"] = update.mqtt_topic
    
    if update.mqtt_username is not None:
        os.environ["VISION_MQTT_USERNAME"] = update.mqtt_username
    
    if update.mqtt_password is not None:
        os.environ["VISION_MQTT_PASSWORD"] = update.mqtt_password
    
    # Update Webhook settings
    if update.webhook_url is not None:
        os.environ["VISION_WEBHOOK_URL"] = update.webhook_url
    
    if update.webhook_headers is not None:
        os.environ["VISION_WEBHOOK_HEADERS"] = update.webhook_headers
    
    return _get_integrations_status()


@router.post("/api/v1/integrations/test/webhook")
async def test_webhook() -> dict:
    """Send a test message to the configured webhook."""
    webhook_url = os.getenv("VISION_WEBHOOK_URL")
    if not webhook_url:
        raise HTTPException(status_code=400, detail="No webhook URL configured")
    
    from app.integrations.webhook import send_webhook
    
    test_payload = {
        "type": "test",
        "message": "Vision webhook test",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    
    try:
        await send_webhook(test_payload)
        return {"ok": True, "url": webhook_url, "message": "Test sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook test failed: {e}")


@router.post("/api/v1/integrations/test/mqtt")
async def test_mqtt() -> dict:
    """Send a test message to the configured MQTT broker."""
    mqtt_broker = os.getenv("VISION_MQTT_BROKER")
    if not mqtt_broker:
        raise HTTPException(status_code=400, detail="No MQTT broker configured")
    
    from app.integrations.mqtt_client import publish_results
    
    test_payload = {
        "type": "test",
        "message": "Vision MQTT test",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    
    try:
        await publish_results(test_payload)
        return {
            "ok": True, 
            "broker": mqtt_broker,
            "topic": os.getenv("VISION_MQTT_TOPIC", "vision/results"),
            "message": "Test message published"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MQTT test failed: {e}")
