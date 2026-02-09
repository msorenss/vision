"""Video inference routes (P13).

Endpoints
---------
POST /api/v1/infer/video                  – upload video, start async job
GET  /api/v1/infer/video/status/{job_id}  – SSE progress stream
GET  /api/v1/infer/video/result/{job_id}  – full result (when done)
POST /api/v1/infer/video/export/{job_id}  – render annotated video (async)
GET  /api/v1/infer/video/export/{job_id}  – download rendered video
GET  /api/v1/infer/video/preview/{job_id} – stream rendered video for playback
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.api.video_schema import (
    FrameDetectionResult,
    VideoExportStatus,
    VideoInferResponse,
    VideoJobStatus,
    VideoSummary,
)
from app.inference.engine import get_engine
from app.inference.video import (
    VideoFrameExtractor,
    save_temp_upload,
)

router = APIRouter(prefix="/api/v1/infer/video", tags=["video"])
logger = logging.getLogger("vision.video")

# ---------------------------------------------------------------------------
# In-memory job store  (sufficient for single-process deployment)
# ---------------------------------------------------------------------------

_jobs: dict[str, dict[str, Any]] = {}


def _new_job() -> str:
    jid = uuid.uuid4().hex[:12]
    _jobs[jid] = {
        "status": "queued",
        "progress": 0.0,
        "frames_done": 0,
        "frames_total": 0,
        "error": None,
        "result": None,
        "source_path": None,      # keep source for rendering
        "rendered_path": None,     # path to rendered MP4
        "render_status": None,     # queued | rendering | done | error
        "render_error": None,
    }
    return jid


def _update_job(jid: str, **kw: Any) -> None:
    if jid in _jobs:
        _jobs[jid].update(kw)


def _get_job(jid: str) -> dict[str, Any] | None:
    return _jobs.get(jid)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _frame_interval() -> int:
    return int(os.getenv("VISION_VIDEO_FRAME_INTERVAL", "5"))


def _max_frames() -> int:
    return int(os.getenv("VISION_VIDEO_MAX_FRAMES", "300"))


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

def _run_video_inference(
    jid: str,
    video_path: Path,
    filter_name: str = "default",
    main_loop: asyncio.AbstractEventLoop | None = None,
) -> None:
    """Synchronous worker – runs in a thread-pool executor."""
    from app.api.routes import _maybe_anonymize_image, _load_filters, _apply_filter  # noqa: E501
    from app.api.routes import _process_integrations  # noqa: E501

    try:
        _update_job(jid, status="processing", source_path=str(video_path))
        engine = get_engine()
        if not engine.loaded:
            _update_job(jid, status="error", error="Model not loaded")
            return

        extractor = VideoFrameExtractor(
            video_path,
            frame_interval=_frame_interval(),
            max_frames=_max_frames(),
        )
        meta = extractor.open()

        # Estimate total frames we will process
        estimated = meta.total_frames // extractor._frame_interval
        if 0 < extractor._max_frames < estimated:
            estimated = extractor._max_frames
        _update_job(jid, frames_total=estimated)

        frames_results: list[FrameDetectionResult] = []
        label_counter: dict[str, int] = defaultdict(int)
        total_dets = 0
        total_privacy_faces = 0

        for fi, pil_image in extractor.extract_frames():
            # Privacy
            privacy_applied = False
            privacy_faces = 0
            try:
                pil_image, privacy_applied, privacy_faces = (
                    _maybe_anonymize_image(pil_image)
                )
            except Exception:
                pass

            # Inference
            detections = engine.predict(pil_image)

            # Apply detection filter
            if filter_name and filter_name != "default":
                try:
                    filters = _load_filters()
                    if filter_name in filters:
                        detections = _apply_filter(
                            detections,
                            filters[filter_name],
                        )
                except Exception:
                    pass

            for d in detections:
                label_counter[d.label] += 1
            total_dets += len(detections)
            total_privacy_faces += privacy_faces

            frames_results.append(
                FrameDetectionResult(
                    frame_index=fi.index,
                    timestamp_ms=fi.timestamp_ms,
                    detections=detections,
                    privacy_applied=privacy_applied,
                    privacy_faces=privacy_faces,
                )
            )

            done = len(frames_results)
            prog = done / max(estimated, 1)
            _update_job(jid, frames_done=done, progress=min(prog, 1.0))

        extractor.close()

        summary = VideoSummary(
            total_frames_analysed=len(frames_results),
            total_detections=total_dets,
            unique_labels=sorted(label_counter.keys()),
            label_counts=dict(label_counter),
            privacy_total_faces=total_privacy_faces,
        )

        result = VideoInferResponse(
            job_id=jid,
            status="done",
            video_width=meta.width,
            video_height=meta.height,
            fps=meta.fps,
            duration_ms=meta.duration_ms,
            frame_interval=extractor._frame_interval,
            frames=frames_results,
            summary=summary,
        )

        _update_job(
            jid,
            status="done",
            progress=1.0,
            frames_done=len(frames_results),
            result=result,
        )

        logger.info(
            "video_done job=%s frames=%d detections=%d",
            jid,
            len(frames_results),
            total_dets,
        )

        # ---- Push results to OPC UA / MQTT / Webhook ----
        # Flatten all detections for the summary payload
        all_detections = []
        for fr in frames_results:
            all_detections.extend(fr.detections)

        if main_loop is not None:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    _process_integrations(
                        all_detections,
                        str(engine.configured_model_path)
                        if engine.configured_model_path else None,
                    ),
                    main_loop,
                )
                # Block until the coroutine finishes (max 30 s)
                future.result(timeout=30)
                logger.info(
                    "video_integrations_ok job=%s dets=%d",
                    jid, len(all_detections),
                )
            except Exception:
                logger.exception("video_integrations_failed job=%s", jid)
        else:
            logger.warning(
                "video_integrations_skipped job=%s",
                jid,
            )

    except Exception as exc:
        logger.exception("video_error job=%s", jid)
        _update_job(jid, status="error", error=str(exc))
        # Clean up temp file on error only
        try:
            video_path.unlink(missing_ok=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=VideoJobStatus)
async def infer_video(
    video: UploadFile = File(...),
    frame_interval: int = Query(
        default=0, ge=0,
        description="Override frame interval (0=use default)",
    ),
    max_frames: int = Query(
        default=0, ge=0,
        description="Override max frames (0=use default)",
    ),
    filter_name: str = Query(
        default="default",
        description="Detection filter to apply",
    ),
):
    """Upload a video file and start async inference.

    Returns a job ID that can be used to poll status or stream SSE progress.
    """
    filename = video.filename or "upload.mp4"
    suffix = Path(filename).suffix.lower()

    if suffix not in {".mp4", ".avi", ".mov", ".mkv", ".webm"}:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported video format:"
                f" {suffix}. Supported:"
                " MP4, AVI, MOV, MKV, WebM"
            ),
        )

    data = await video.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty video file")

    tmp_path = save_temp_upload(data, suffix=suffix)

    jid = _new_job()

    # Override config per request if provided
    if frame_interval > 0:
        os.environ["VISION_VIDEO_FRAME_INTERVAL"] = str(frame_interval)
    if max_frames > 0:
        os.environ["VISION_VIDEO_MAX_FRAMES"] = str(max_frames)

    loop = asyncio.get_running_loop()
    loop.run_in_executor(
        None, _run_video_inference,
        jid, tmp_path, filter_name, loop,
    )

    return VideoJobStatus(
        job_id=jid,
        status="queued",
        frames_total=0,
    )


@router.get("/status/{job_id}")
async def video_status_sse(job_id: str):
    """Server-Sent Events stream of job progress.

    Sends JSON-encoded VideoJobStatus objects.  Closes when the job
    reaches ``done`` or ``error``.
    """
    job = _get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    async def _generate():
        while True:
            j = _get_job(job_id)
            if j is None:
                break

            payload = VideoJobStatus(
                job_id=job_id,
                status=j["status"],
                progress=j["progress"],
                frames_done=j["frames_done"],
                frames_total=j["frames_total"],
                error=j.get("error"),
            )
            yield f"data: {payload.model_dump_json()}\n\n"

            if j["status"] in {"done", "error"}:
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/result/{job_id}", response_model=VideoInferResponse)
async def video_result(job_id: str):
    """Retrieve the full result once the job is done."""
    job = _get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] == "error":
        raise HTTPException(
            status_code=500,
            detail=job.get("error", "Unknown error"),
        )

    if job["status"] != "done":
        raise HTTPException(
            status_code=202,
            detail=(
                f"Job still {job['status']}."
                f" Poll /status/{job_id}"
                " for progress."
            ),
        )

    return job["result"]


# ---------------------------------------------------------------------------
# Render / Export endpoints
# ---------------------------------------------------------------------------

def _run_render(jid: str, opts: dict) -> None:
    """Background render worker."""
    from app.inference.video_render import render_annotated_video

    try:
        _update_job(jid, render_status="rendering")
        job = _get_job(jid)
        if job is None:
            return

        source = Path(job["source_path"])
        if not source.exists():
            _update_job(
                jid,
                render_status="error",
                render_error="Source video no longer available",
            )
            return

        result: VideoInferResponse = job["result"]
        frames_data = [
            fr.model_dump() for fr in result.frames
        ]

        out = render_annotated_video(
            source,
            frames_data,
            draw_boxes=opts.get("boxes", True),
            draw_labels=opts.get("labels", True),
            apply_privacy=opts.get("privacy", True),
            frame_interval=result.frame_interval,
        )

        _update_job(
            jid,
            render_status="done",
            rendered_path=str(out),
        )
        logger.info("render_done job=%s path=%s", jid, out)

    except Exception as exc:
        logger.exception("render_error job=%s", jid)
        _update_job(
            jid,
            render_status="error",
            render_error=str(exc),
        )


@router.post(
    "/export/{job_id}",
    response_model=VideoExportStatus,
)
async def start_export(
    job_id: str,
    boxes: bool = Query(default=True, description="Draw bounding boxes"),
    labels: bool = Query(default=True, description="Draw labels on boxes"),
    privacy: bool = Query(default=True, description="Apply face blur"),
):
    """Start rendering an annotated video for a completed job."""
    job = _get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "done":
        raise HTTPException(
            status_code=400,
            detail="Inference not done yet",
        )
    if not job.get("source_path"):
        raise HTTPException(
            status_code=410,
            detail="Source video no longer available",
        )

    _update_job(job_id, render_status="queued", rendered_path=None)

    loop = asyncio.get_running_loop()
    loop.run_in_executor(
        None,
        _run_render,
        job_id,
        {"boxes": boxes, "labels": labels, "privacy": privacy},
    )

    return VideoExportStatus(
        job_id=job_id,
        render_status="queued",
    )


@router.get(
    "/export/{job_id}",
    response_model=None,
)
async def download_export(job_id: str):
    """Download the rendered annotated video.

    Returns the render status if not done, or the MP4 file if ready.
    """
    job = _get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    rs = job.get("render_status")
    if rs == "error":
        raise HTTPException(
            status_code=500,
            detail=job.get("render_error", "Render failed"),
        )
    if rs != "done":
        return VideoExportStatus(
            job_id=job_id,
            render_status=rs or "not_started",
        )

    rendered = job.get("rendered_path")
    if not rendered or not Path(rendered).exists():
        raise HTTPException(
            status_code=410,
            detail="Rendered file not found",
        )

    return FileResponse(
        rendered,
        media_type="video/mp4",
        filename=f"vision_{job_id}_annotated.mp4",
    )


@router.get("/preview/{job_id}")
async def preview_video(job_id: str):
    """Stream the rendered video for in-browser playback.

    Returns 202 with status JSON if rendering is not yet done.
    """
    job = _get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    rs = job.get("render_status")
    if rs != "done":
        raise HTTPException(
            status_code=202,
            detail=f"Render status: {rs or 'not_started'}",
        )

    rendered = job.get("rendered_path")
    if not rendered or not Path(rendered).exists():
        raise HTTPException(
            status_code=410,
            detail="Rendered file not found",
        )

    return FileResponse(
        rendered,
        media_type="video/mp4",
        headers={"Accept-Ranges": "bytes"},
    )
