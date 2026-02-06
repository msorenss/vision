"""Training API routes (P10)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.api.training_schema import (
    ExportRequest,
    ExportResponse,
    TrainingConfig,
    TrainingHistoryResponse,
    TrainingJob,
    TrainingLogsResponse,
    TrainingMetrics,
    TrainingStartResponse,
    TrainingStatus,
    TrainingStopResponse,
)
from app.training.worker import (
    export_to_bundle,
    get_current_job,
    get_job_history,
    get_training_logs,
    start_training,
    stop_training,
)

router = APIRouter(prefix="/api/v1/training", tags=["training"])


@router.post("/start", response_model=TrainingStartResponse)
def start_training_job(config: TrainingConfig) -> TrainingStartResponse:
    """Start a new training job."""
    success, job_id, message = start_training(config.model_dump())
    
    if not success:
        raise HTTPException(status_code=409, detail=message)
    
    return TrainingStartResponse(
        ok=True,
        job_id=job_id,
        message=message,
    )


@router.get("/status", response_model=TrainingStatus)
def get_training_status() -> TrainingStatus:
    """Get status of current/last training job."""
    job = get_current_job()
    
    if job is None:
        # Check history for last job
        history = get_job_history()
        if history:
            last = history[0]
            return TrainingStatus(
                job_id=last["job_id"],
                status=last["status"],
                dataset=last["dataset"],
                current_epoch=last.get("epochs_completed", 0),
                started_at=last.get("started_at"),
                finished_at=last.get("finished_at"),
                best_map50=last.get("best_map50"),
                output_path=last.get("output_bundle"),
            )
        
        raise HTTPException(status_code=404, detail="No training jobs found")
    
    # Calculate progress
    progress = 0.0
    if job.total_epochs > 0:
        progress = (job.current_epoch / job.total_epochs) * 100
    
    # Calculate elapsed time
    elapsed = 0.0
    eta = None
    if job.started_at:
        elapsed = (datetime.utcnow() - job.started_at).total_seconds()
        if job.current_epoch > 0 and job.total_epochs > job.current_epoch:
            time_per_epoch = elapsed / job.current_epoch
            remaining_epochs = job.total_epochs - job.current_epoch
            eta = time_per_epoch * remaining_epochs
    
    # Build metrics
    metrics = None
    if job.metrics:
        metrics = TrainingMetrics(**job.metrics)
    
    return TrainingStatus(
        job_id=job.job_id,
        status=job.status,
        dataset=job.dataset,
        current_epoch=job.current_epoch,
        total_epochs=job.total_epochs,
        progress_percent=progress,
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
        elapsed_seconds=elapsed,
        eta_seconds=eta,
        metrics=metrics,
        best_map50=job.best_map50,
        output_path=job.output_path,
        error_message=job.error_message,
        config=TrainingConfig(**job.config),
    )


@router.post("/stop", response_model=TrainingStopResponse)
def stop_training_job() -> TrainingStopResponse:
    """Stop the current training job."""
    success, message = stop_training()
    
    job = get_current_job()
    job_id = job.job_id if job else "unknown"
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return TrainingStopResponse(
        ok=True,
        job_id=job_id,
        message=message,
    )


@router.get("/logs", response_model=TrainingLogsResponse)
def get_logs(job_id: str | None = None) -> TrainingLogsResponse:
    """Get training logs."""
    logs = get_training_logs(job_id)
    
    current_job = get_current_job()
    actual_job_id = job_id or (current_job.job_id if current_job else "unknown")
    
    return TrainingLogsResponse(
        job_id=actual_job_id,
        logs=logs[-100:],  # Last 100 lines
        total_lines=len(logs),
    )


@router.get("/history", response_model=TrainingHistoryResponse)
def get_history() -> TrainingHistoryResponse:
    """Get training job history."""
    history = get_job_history()
    
    jobs = [
        TrainingJob(
            job_id=h["job_id"],
            dataset=h["dataset"],
            status=h["status"],
            started_at=h["started_at"] or "",
            finished_at=h.get("finished_at"),
            epochs_completed=h.get("epochs_completed", 0),
            best_map50=h.get("best_map50"),
            output_bundle=h.get("output_bundle"),
        )
        for h in history
    ]
    
    return TrainingHistoryResponse(jobs=jobs)


@router.post("/export", response_model=ExportResponse)
def export_model(req: ExportRequest) -> ExportResponse:
    """Export a trained model to a bundle."""
    success, result, files = export_to_bundle(
        model_path=req.model_path,
        bundle_name=req.bundle_name,
        bundle_version=req.bundle_version,
        format=req.format,
        img_size=req.img_size,
        opset=req.opset,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=result)
    
    return ExportResponse(
        ok=True,
        format=req.format,
        bundle_path=result,
        files=files,
    )


@router.post("/export/openvino", response_model=ExportResponse)
def export_model_openvino(
    model_path: str,
    bundle_name: str,
    bundle_version: str = "v1",
    img_size: int = 640,
) -> ExportResponse:
    """Export a trained model to OpenVINO format."""
    success, result, files = export_to_bundle(
        model_path=model_path,
        bundle_name=bundle_name,
        bundle_version=bundle_version,
        format="openvino",
        img_size=img_size,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=result)
    
    return ExportResponse(
        ok=True,
        format="openvino",
        bundle_path=result,
        files=files,
    )
