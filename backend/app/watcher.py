from __future__ import annotations

import asyncio
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PIL import Image
from watchfiles import Change, awatch

from app.inference.engine import get_engine
from app.inference.video import (
    VideoFrameExtractor, is_video_file,
)
from app.integrations import webhook, mqtt_client
from app.integrations.opcua_server import server_instance as opcua_server


@dataclass
class WatchConfig:
    enabled: bool
    input_dir: Path
    output_dir: Path
    processed_dir: Path | None  # Where to move processed images
    mode: Literal["json", "move", "both", "annotated"]  # Output mode
    export_annotated: bool = False  # Also save annotated images
    export_format: str = "jpg"  # jpg or png


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_watch_config() -> WatchConfig:
    """Load watch configuration from environment variables.

    Environment variables:
    - VISION_WATCH: Enable folder watching (1/true to enable)
    - VISION_WATCH_INPUT: Input folder to watch (default: /input)
    - VISION_WATCH_OUTPUT: Output folder for JSON results (default: /output)
    - VISION_WATCH_PROCESSED: Folder to move processed images to (optional)
    - VISION_WATCH_MODE: Output mode - 'json', 'move',
      or 'both' (default: both if processed dir set)
    """
    enabled = _truthy(os.getenv("VISION_WATCH"))
    input_dir = Path(os.getenv("VISION_WATCH_INPUT", "/input"))
    output_dir = Path(os.getenv("VISION_WATCH_OUTPUT", "/output"))

    processed_env = os.getenv("VISION_WATCH_PROCESSED", "")
    processed_dir = Path(processed_env) if processed_env else None

    mode_env = os.getenv("VISION_WATCH_MODE", "").lower()
    if mode_env in {"json", "move", "both", "annotated"}:
        mode = mode_env  # type: ignore
    elif processed_dir:
        mode = "both"  # Default to both if processed dir is set
    else:
        mode = "json"  # Default to json only

    export_annotated = (
        _truthy(os.getenv("VISION_EXPORT_ANNOTATED"))
        or mode == "annotated"
    )
    export_format = os.getenv(
        "VISION_EXPORT_FORMAT", "jpg",
    ).lower().strip()
    if export_format not in {"jpg", "jpeg", "png"}:
        export_format = "jpg"

    return WatchConfig(
        enabled=enabled,
        input_dir=input_dir,
        output_dir=output_dir,
        processed_dir=processed_dir,
        mode=mode,
        export_annotated=export_annotated,
        export_format=export_format,
    )


def _is_image(path: Path) -> bool:
    return path.suffix.lower() in {
        ".jpg", ".jpeg", ".png", ".bmp",
        ".webp", ".heic", ".heif",
    }


def _is_media(path: Path) -> bool:
    """Return True for both image and video files."""
    return _is_image(path) or is_video_file(path)


async def _wait_for_stable_file(
    path: Path,
    checks: int = 5,
    delay_s: float = 0.2,
) -> None:
    """Wait until file size is stable to avoid reading while being written."""

    last_size = -1
    for _ in range(checks):
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            await asyncio.sleep(delay_s)
            continue

        if size == last_size and size > 0:
            return
        last_size = size
        await asyncio.sleep(delay_s)


def _output_json_path(cfg: WatchConfig, image_path: Path) -> Path:
    # Preserve relative folder structure.
    try:
        rel = image_path.relative_to(cfg.input_dir)
    except ValueError:
        rel = image_path.name

    rel_path = Path(rel)
    out_dir = cfg.output_dir / rel_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{rel_path.stem}.detections.json"


def _processed_image_path(cfg: WatchConfig, image_path: Path) -> Path | None:
    """Get the destination path for a processed image."""
    if not cfg.processed_dir:
        return None

    # Preserve relative folder structure
    try:
        rel = image_path.relative_to(cfg.input_dir)
    except ValueError:
        rel = Path(image_path.name)

    dest_dir = cfg.processed_dir / rel.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir / rel.name


def _move_to_processed(cfg: WatchConfig, image_path: Path) -> Path | None:
    """Move an image to the processed folder."""
    dest = _processed_image_path(cfg, image_path)
    if not dest:
        return None

    try:
        # Use shutil.move to handle cross-device moves
        shutil.move(str(image_path), str(dest))
        return dest
    except Exception:
        # If move fails, try copy + delete
        try:
            shutil.copy2(str(image_path), str(dest))
            image_path.unlink()
            return dest
        except Exception:
            return None


def _save_annotated_image(
    cfg: WatchConfig,
    image_path: Path,
    pil: Image.Image,
    detections: list,
) -> Path | None:
    """Save an annotated version of the image to the output dir."""
    try:
        from app.inference.image_export import ImageAnnotator

        annotator = ImageAnnotator()
        annotated = annotator.annotate(pil, detections)

        try:
            rel = image_path.relative_to(cfg.input_dir)
        except ValueError:
            rel = Path(image_path.name)

        out_dir = cfg.output_dir / rel.parent
        out_dir.mkdir(parents=True, exist_ok=True)

        ext = cfg.export_format
        if ext in ("jpg", "jpeg"):
            out_path = out_dir / f"{rel.stem}_annotated.jpg"
            annotated.save(out_path, format="JPEG", quality=90)
        else:
            out_path = out_dir / f"{rel.stem}_annotated.png"
            annotated.save(out_path, format="PNG")

        print(f"[watcher] Saved annotated: {out_path}")
        return out_path
    except Exception as exc:
        print(
            f"[watcher] Failed to save annotated "
            f"{image_path.name}: {exc}",
        )
        return None


async def run_watch_loop() -> None:
    """Main watch loop that monitors input folder for new images.

    When a new image is detected:
    1. Waits for the file to be fully written
    2. Runs inference on the image
    3. Depending on mode:
       - 'json': Writes detection results to output folder
       - 'move': Moves image to processed folder
       - 'both': Both writes JSON and moves image
    """
    cfg = load_watch_config()
    if not cfg.enabled:
        return

    # Start OPC UA Server (if enabled via env)
    await opcua_server.start()

    cfg.input_dir.mkdir(parents=True, exist_ok=True)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    if cfg.processed_dir:
        cfg.processed_dir.mkdir(parents=True, exist_ok=True)

    print(f"[watcher] Watching {cfg.input_dir} for images...")
    processed = cfg.processed_dir or '(disabled)'
    print(
        f"[watcher] Output: {cfg.output_dir}, "
        f"Processed: {processed}",
    )
    print(f"[watcher] Mode: {cfg.mode}")

    engine = None

    async for changes in awatch(cfg.input_dir):
        if engine is None:
            try:
                engine = get_engine()
            except Exception:
                # If model can't be loaded yet, retry later.
                await asyncio.sleep(1.0)
                continue

        for change, file_str in changes:
            if change not in {Change.added, Change.modified}:
                continue

            path = Path(file_str)
            if not _is_media(path):
                continue

            # Skip files already in processed folder
            if cfg.processed_dir:
                try:
                    path.relative_to(cfg.processed_dir)
                    continue  # File is in processed folder, skip
                except ValueError:
                    pass  # Not in processed folder, continue

            out_json = _output_json_path(cfg, path)

            # Skip if already processed (JSON exists or file was moved)
            if out_json.exists():
                continue

            await _wait_for_stable_file(path)

            # Double-check file still exists
            if not path.exists():
                continue

            print(f"[watcher] Processing: {path.name}")

            # --- Video files ---
            if is_video_file(path):
                await _process_video(cfg, path, engine, out_json)
                continue

            # --- Image files ---
            try:
                pil = Image.open(path).convert("RGB")
            except Exception as e:
                print(f"[watcher] Failed to open {path.name}: {e}")
                continue

            try:
                detections = engine.predict(pil)
            except Exception as exc:  # noqa: BLE001
                # Write error JSON if in json or both mode
                if cfg.mode in {"json", "both"}:
                    out_json.write_text(
                        json.dumps(
                            {
                                "ok": False,
                                "error": str(exc),
                                "image": str(path),
                            },
                            indent=2,
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                print(f"[watcher] Inference failed for {path.name}: {exc}")
                continue

            # Write annotated image if configured (P15)
            if cfg.export_annotated or cfg.mode == "annotated":
                _save_annotated_image(
                    cfg, path, pil, detections,
                )

            # Write JSON result if in json or both mode
            # Prepare payload for all outputs
            payload = {
                "ok": True,
                "image": str(path),
                "image_width": pil.width,
                "image_height": pil.height,
                "detections": [d.model_dump() for d in detections],
            }

            # Integrations
            asyncio.create_task(webhook.send_webhook(payload))
            asyncio.create_task(mqtt_client.publish_results(payload))
            asyncio.create_task(
                opcua_server.update_result(
                    payload,
                    engine.configured_model_path
                    or "Unknown",
                ),
            )

            # Write JSON result to disk if configured
            if cfg.mode in {"json", "both"}:
                out_json.write_text(
                    json.dumps(payload, indent=2) + "\n",
                    encoding="utf-8",
                )

            # Move to processed folder if in move or both mode
            if cfg.mode in {"move", "both"} and cfg.processed_dir:
                dest = _move_to_processed(cfg, path)
                if dest:
                    print(f"[watcher] Moved to: {dest}")
                    # Update JSON with new location if we wrote it
                    if cfg.mode == "both" and out_json.exists():
                        try:
                            data = json.loads(
                                out_json.read_text(
                                    encoding="utf-8",
                                ),
                            )
                            data["processed_path"] = str(dest)
                            out_json.write_text(
                                json.dumps(data, indent=2) + "\n",
                                encoding="utf-8",
                            )
                        except Exception:
                            pass

            det_count = len(detections)
            print(f"[watcher] Done: {path.name} -> {det_count} detections")


async def _process_video(
    cfg: WatchConfig,
    path: Path,
    engine,
    out_json: Path,
) -> None:
    """Process a video file from the watch folder."""
    import os as _os
    from collections import defaultdict

    frame_interval = int(_os.getenv("VISION_VIDEO_FRAME_INTERVAL", "5"))
    max_frames = int(_os.getenv("VISION_VIDEO_MAX_FRAMES", "300"))

    try:
        extractor = VideoFrameExtractor(
            path,
            frame_interval=frame_interval,
            max_frames=max_frames,
        )
        meta = extractor.open()
    except Exception as exc:
        print(f"[watcher] Failed to open video {path.name}: {exc}")
        if cfg.mode in {"json", "both"}:
            out_json.write_text(
                json.dumps(
                    {
                        "ok": False,
                        "error": str(exc),
                        "video": str(path),
                    },
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
        return

    frames_out: list[dict] = []
    label_counter: dict[str, int] = defaultdict(int)
    total_dets = 0

    for fi, pil_image in extractor.extract_frames():
        try:
            detections = engine.predict(pil_image)
        except Exception as exc:
            print(
                f"[watcher] Inference failed on frame"
                f" {fi.index} of {path.name}: {exc}",
            )
            continue

        for d in detections:
            label_counter[d.label] += 1
        total_dets += len(detections)

        frames_out.append({
            "frame_index": fi.index,
            "timestamp_ms": fi.timestamp_ms,
            "detections": [d.model_dump() for d in detections],
        })

    extractor.close()

    payload = {
        "ok": True,
        "type": "video",
        "video": str(path),
        "video_width": meta.width,
        "video_height": meta.height,
        "fps": meta.fps,
        "duration_ms": meta.duration_ms,
        "frame_interval": frame_interval,
        "frames_analysed": len(frames_out),
        "total_detections": total_dets,
        "unique_labels": sorted(label_counter.keys()),
        "label_counts": dict(label_counter),
        "frames": frames_out,
    }

    # Integrations
    summary_payload = {k: v for k, v in payload.items() if k != "frames"}
    asyncio.create_task(webhook.send_webhook(summary_payload))
    asyncio.create_task(mqtt_client.publish_results(summary_payload))
    model_path = engine.configured_model_path or "Unknown"
    asyncio.create_task(
        opcua_server.update_result(
            summary_payload, model_path,
        ),
    )

    if cfg.mode in {"json", "both"}:
        out_json.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )

    if cfg.mode in {"move", "both"} and cfg.processed_dir:
        dest = _move_to_processed(cfg, path)
        if dest:
            print(f"[watcher] Moved to: {dest}")

    print(
        f"[watcher] Done video: {path.name} -> "
        f"{len(frames_out)} frames, "
        f"{total_dets} detections",
    )
