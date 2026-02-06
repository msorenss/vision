"""Training worker for YOLO training (P10).

This module handles asynchronous training jobs using ultralytics YOLO.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class TrainingJobState:
    """Internal state of a training job."""
    
    job_id: str
    dataset: str
    config: dict
    status: Literal["queued", "running", "completed", "failed", "stopped"] = "queued"
    
    # Progress
    current_epoch: int = 0
    total_epochs: int = 0
    
    # Timing
    started_at: datetime | None = None
    finished_at: datetime | None = None
    
    # Results
    metrics: dict | None = None
    best_map50: float | None = None
    output_path: str | None = None
    error_message: str | None = None
    
    # Internal
    logs: list[str] = field(default_factory=list)
    stop_requested: bool = False
    thread: threading.Thread | None = None


# Global state
_current_job: TrainingJobState | None = None
_job_history: list[TrainingJobState] = []
_lock = threading.Lock()


def _output_dir() -> Path:
    """Get training output directory."""
    env_path = os.getenv("VISION_TRAINING_OUTPUT")
    if env_path:
        return Path(env_path).resolve()
    return Path("/training_output")


def _models_dir() -> Path:
    """Get models directory for bundle output."""
    env_path = os.getenv("VISION_MODELS_DIR")
    if env_path:
        return Path(env_path).resolve()
    
    docker_path = Path("/models")
    if docker_path.exists():
        return docker_path
    
    return Path(__file__).parent.parent.parent.parent / "models"


def _datasets_dir() -> Path:
    """Get datasets directory."""
    env_path = os.getenv("VISION_DATASETS_DIR")
    if env_path:
        return Path(env_path).resolve()
    
    docker_path = Path("/datasets")
    if docker_path.exists():
        return docker_path
    
    return Path(__file__).parent.parent.parent.parent / "datasets"


def get_current_job() -> TrainingJobState | None:
    """Get the currently running/queued job."""
    with _lock:
        return _current_job


def get_job_history() -> list[dict]:
    """Get historical jobs as dicts."""
    with _lock:
        return [
            {
                "job_id": job.job_id,
                "dataset": job.dataset,
                "status": job.status,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "finished_at": job.finished_at.isoformat() if job.finished_at else None,
                "epochs_completed": job.current_epoch,
                "best_map50": job.best_map50,
                "output_bundle": job.output_path,
            }
            for job in reversed(_job_history[-20:])  # Last 20 jobs
        ]


def _run_training(job: TrainingJobState) -> None:
    """Run training in a background thread."""
    global _current_job
    
    try:
        job.status = "running"
        job.started_at = datetime.utcnow()
        job.logs.append(f"[{datetime.utcnow().isoformat()}] Training started")
        
        # Import ultralytics
        try:
            from ultralytics import YOLO
        except ImportError as e:
            job.status = "failed"
            job.error_message = "ultralytics not installed. Run: pip install ultralytics"
            job.logs.append(f"[{datetime.utcnow().isoformat()}] ERROR: {job.error_message}")
            return
        
        config = job.config
        dataset_path = _datasets_dir() / job.dataset
        yaml_path = dataset_path / "dataset.yaml"
        
        if not yaml_path.exists():
            job.status = "failed"
            job.error_message = f"dataset.yaml not found in {dataset_path}"
            job.logs.append(f"[{datetime.utcnow().isoformat()}] ERROR: {job.error_message}")
            return
        
        # Create output directory
        output_dir = _output_dir() / job.job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        job.logs.append(f"[{datetime.utcnow().isoformat()}] Loading model: {config['model_variant']}")
        
        # Load model
        model_variant = config.get("model_variant", "yolov8n")
        if config.get("pretrained", True):
            model = YOLO(f"{model_variant}.pt")
        else:
            model = YOLO(f"{model_variant}.yaml")
        
        job.total_epochs = config.get("epochs", 100)
        job.logs.append(f"[{datetime.utcnow().isoformat()}] Starting training for {job.total_epochs} epochs")
        
        # Callback for progress updates
        def on_train_epoch_end(trainer):
            if job.stop_requested:
                trainer.stop = True
                return
            
            job.current_epoch = trainer.epoch + 1
            
            # Extract metrics
            if hasattr(trainer, "metrics"):
                m = trainer.metrics
                job.metrics = {
                    "epoch": job.current_epoch,
                    "box_loss": getattr(m, "box_loss", None),
                    "cls_loss": getattr(m, "cls_loss", None),
                    "precision": m.get("metrics/precision(B)", None) if isinstance(m, dict) else None,
                    "recall": m.get("metrics/recall(B)", None) if isinstance(m, dict) else None,
                    "map50": m.get("metrics/mAP50(B)", None) if isinstance(m, dict) else None,
                    "map50_95": m.get("metrics/mAP50-95(B)", None) if isinstance(m, dict) else None,
                }
                
                # Track best mAP
                map50 = job.metrics.get("map50")
                if map50 is not None and (job.best_map50 is None or map50 > job.best_map50):
                    job.best_map50 = map50
            
            job.logs.append(
                f"[{datetime.utcnow().isoformat()}] Epoch {job.current_epoch}/{job.total_epochs} "
                f"- mAP50: {job.best_map50 or 'N/A'}"
            )
        
        # Add callback
        model.add_callback("on_train_epoch_end", on_train_epoch_end)
        
        # Run training
        results = model.train(
            data=str(yaml_path),
            epochs=config.get("epochs", 100),
            batch=config.get("batch_size", 16),
            imgsz=config.get("img_size", 640),
            device=config.get("device", "cpu"),
            patience=config.get("patience", 50),
            lr0=config.get("lr0", 0.01),
            augment=config.get("augment", True),
            project=str(output_dir),
            name="train",
            exist_ok=True,
            verbose=False,
        )
        
        if job.stop_requested:
            job.status = "stopped"
            job.logs.append(f"[{datetime.utcnow().isoformat()}] Training stopped by user")
        else:
            job.status = "completed"
            job.logs.append(f"[{datetime.utcnow().isoformat()}] Training completed successfully")
            
            # Get best model path
            best_pt = output_dir / "train" / "weights" / "best.pt"
            if best_pt.exists():
                job.output_path = str(best_pt)
                job.logs.append(f"[{datetime.utcnow().isoformat()}] Best model saved to: {best_pt}")
        
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.logs.append(f"[{datetime.utcnow().isoformat()}] ERROR: {e}")
        logger.exception(f"Training failed for job {job.job_id}")
    
    finally:
        job.finished_at = datetime.utcnow()
        
        with _lock:
            global _current_job
            _job_history.append(job)
            _current_job = None


def start_training(config: dict) -> tuple[bool, str, str]:
    """Start a new training job.
    
    Returns: (success, job_id, message)
    """
    global _current_job
    
    with _lock:
        if _current_job is not None and _current_job.status in ("queued", "running"):
            return False, "", "A training job is already running"
        
        job_id = str(uuid.uuid4())[:8]
        
        job = TrainingJobState(
            job_id=job_id,
            dataset=config["dataset"],
            config=config,
            total_epochs=config.get("epochs", 100),
        )
        
        _current_job = job
        
        # Start training thread
        thread = threading.Thread(target=_run_training, args=(job,), daemon=True)
        job.thread = thread
        thread.start()
        
        return True, job_id, f"Training started with job ID: {job_id}"


def stop_training() -> tuple[bool, str]:
    """Stop the current training job.
    
    Returns: (success, message)
    """
    with _lock:
        if _current_job is None:
            return False, "No training job running"
        
        if _current_job.status not in ("queued", "running"):
            return False, f"Job is already {_current_job.status}"
        
        _current_job.stop_requested = True
        return True, f"Stop requested for job {_current_job.job_id}"


def get_training_logs(job_id: str | None = None) -> list[str]:
    """Get logs for a job."""
    with _lock:
        if job_id is None and _current_job:
            return list(_current_job.logs)
        
        for job in _job_history:
            if job.job_id == job_id:
                return list(job.logs)
        
        if _current_job and _current_job.job_id == job_id:
            return list(_current_job.logs)
        
        return []


def export_to_bundle(
    model_path: str,
    bundle_name: str,
    bundle_version: str,
    format: str = "onnx",
    img_size: int = 640,
    opset: int = 17,
) -> tuple[bool, str, list[str]]:
    """Export a trained model to a bundle.
    
    Returns: (success, bundle_path, files)
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        return False, "ultralytics not installed", []
    
    model_path = Path(model_path)
    if not model_path.exists():
        return False, f"Model not found: {model_path}", []
    
    # Load model
    model = YOLO(str(model_path))
    
    # Create bundle directory
    bundle_dir = _models_dir() / bundle_name / bundle_version
    bundle_dir.mkdir(parents=True, exist_ok=True)
    
    files = []
    
    if format == "onnx":
        # Export to ONNX
        export_path = model.export(format="onnx", imgsz=img_size, opset=opset)
        
        # Move to bundle
        onnx_file = bundle_dir / "model.onnx"
        shutil.move(str(export_path), str(onnx_file))
        files.append("model.onnx")
        
    elif format == "openvino":
        # Export to OpenVINO
        export_path = model.export(format="openvino", imgsz=img_size)
        
        # OpenVINO creates a directory, move contents
        export_dir = Path(export_path)
        for f in export_dir.iterdir():
            dest = bundle_dir / f.name
            shutil.move(str(f), str(dest))
            files.append(f.name)
        
        # Clean up empty export dir
        if export_dir.exists() and export_dir.is_dir():
            export_dir.rmdir()
    
    # Copy labels from model's data.yaml if available
    if hasattr(model, "names") and model.names:
        labels_path = bundle_dir / "labels.txt"
        labels = [model.names[i] for i in sorted(model.names.keys())]
        labels_path.write_text("\n".join(labels) + "\n", encoding="utf-8")
        files.append("labels.txt")
    
    # Create meta.json
    meta = {
        "exported_at": datetime.utcnow().isoformat(),
        "format": format,
        "source_model": str(model_path),
        "img_size": img_size,
    }
    if format == "onnx":
        meta["opset"] = opset
    
    meta_path = bundle_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    files.append("meta.json")
    
    return True, str(bundle_dir), files
