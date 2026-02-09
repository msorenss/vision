"""Render annotated video with bounding boxes and privacy blur.

Uses OpenCV VideoWriter to produce an MP4 file from the original
video combined with per-frame detection results and optional privacy
anonymization.

Key features:
- Detections are **interpolated** between analysed key-frames so that
  bounding boxes glide smoothly instead of flickering on/off.
- The raw render (mp4v) is automatically re-encoded to H.264 via
  ``ffmpeg`` so the result plays natively in every modern browser.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.api.schema import Box, Detection

logger = logging.getLogger("vision.video.render")

# Volvo Cars palette (same as frontend)
COLORS = [
    (0, 48, 87),      # #003057
    (211, 96, 0),     # #d36000
    (26, 135, 84),    # #1a8754
    (74, 158, 255),   # #4a9eff
    (196, 18, 48),    # #c41230
    (0, 77, 140),     # #004d8c
    (255, 133, 51),   # #ff8533
    (46, 204, 113),   # #2ecc71
    (109, 179, 255),  # #6db3ff
    (231, 76, 60),    # #e74c3c
]


# ------------------------------------------------------------------
# Colour helpers
# ------------------------------------------------------------------

def _bgr(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Convert RGB to BGR for OpenCV."""
    return (rgb[2], rgb[1], rgb[0])


# ------------------------------------------------------------------
# Interpolation helpers
# ------------------------------------------------------------------

def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between *a* and *b* at fraction *t*."""
    return a + (b - a) * t


def _interpolate_box(box_a: Box, box_b: Box, t: float) -> Box:
    """Linearly interpolate two bounding boxes."""
    return Box(
        x1=_lerp(box_a.x1, box_b.x1, t),
        y1=_lerp(box_a.y1, box_b.y1, t),
        x2=_lerp(box_a.x2, box_b.x2, t),
        y2=_lerp(box_a.y2, box_b.y2, t),
    )


def _match_detections(
    prev: list[Detection],
    curr: list[Detection],
) -> list[tuple[Detection, Detection]]:
    """Greedy match detections between two key-frames by label + IoU.

    Returns pairs (prev_det, curr_det) for interpolation.  Unmatched
    detections in *curr* are paired with themselves so they still show.
    """
    used_prev: set[int] = set()
    used_curr: set[int] = set()
    pairs: list[tuple[Detection, Detection]] = []

    for ci, cd in enumerate(curr):
        best_iou = 0.3  # minimum IoU threshold to match
        best_pi = -1
        for pi, pd in enumerate(prev):
            if pi in used_prev:
                continue
            if pd.label != cd.label:
                continue
            iou = _iou(pd.box, cd.box)
            if iou > best_iou:
                best_iou = iou
                best_pi = pi
        if best_pi >= 0:
            pairs.append((prev[best_pi], cd))
            used_prev.add(best_pi)
            used_curr.add(ci)
        else:
            # No match – fade in from same position
            pairs.append((cd, cd))
            used_curr.add(ci)

    return pairs


def _iou(a: Box, b: Box) -> float:
    """Intersection-over-Union of two boxes."""
    ix1 = max(a.x1, b.x1)
    iy1 = max(a.y1, b.y1)
    ix2 = min(a.x2, b.x2)
    iy2 = min(a.y2, b.y2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    area_a = max(0, a.x2 - a.x1) * max(0, a.y2 - a.y1)
    area_b = max(0, b.x2 - b.x1) * max(0, b.y2 - b.y1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _build_interpolated_detections(
    frame_det_map: dict[int, list[Detection]],
    total_frames: int,
) -> dict[int, list[Detection]]:
    """Build a per-frame detection map with smooth interpolation.

    Analysed key-frames keep their exact detections.  Frames between
    two key-frames get linearly interpolated bounding boxes.  Frames
    before the first or after the last key-frame carry-forward /
    carry-back the nearest key-frame detections (no interpolation).
    """
    if not frame_det_map:
        return {}

    sorted_keys = sorted(frame_det_map.keys())
    full: dict[int, list[Detection]] = {}

    # Copy key-frames as-is
    for k in sorted_keys:
        full[k] = frame_det_map[k]

    # Carry-back: frames before first key-frame
    first_key = sorted_keys[0]
    for fi in range(0, first_key):
        full[fi] = frame_det_map[first_key]

    # Carry-forward: frames after last key-frame
    last_key = sorted_keys[-1]
    for fi in range(last_key + 1, total_frames):
        full[fi] = frame_det_map[last_key]

    # Interpolate between consecutive key-frames
    for ki in range(len(sorted_keys) - 1):
        ka = sorted_keys[ki]
        kb = sorted_keys[ki + 1]
        gap = kb - ka
        if gap <= 1:
            continue  # adjacent – nothing to interpolate

        dets_a = frame_det_map[ka]
        dets_b = frame_det_map[kb]

        pairs = _match_detections(dets_a, dets_b)

        for fi in range(ka + 1, kb):
            t = (fi - ka) / gap
            interp_dets: list[Detection] = []
            for det_a, det_b in pairs:
                interp_dets.append(
                    Detection(
                        class_id=det_b.class_id,
                        label=det_b.label,
                        score=_lerp(det_a.score, det_b.score, t),
                        box=_interpolate_box(det_a.box, det_b.box, t),
                    )
                )
            full[fi] = interp_dets

    return full


# ------------------------------------------------------------------
# Drawing helpers
# ------------------------------------------------------------------

def _draw_boxes_on_frame(
    frame_bgr: np.ndarray,
    detections: list[Detection],
    *,
    draw_labels: bool = True,
) -> np.ndarray:
    """Draw bounding boxes + labels onto an OpenCV BGR frame."""
    for i, det in enumerate(detections):
        color = _bgr(COLORS[i % len(COLORS)])
        x1 = int(det.box.x1)
        y1 = int(det.box.y1)
        x2 = int(det.box.x2)
        y2 = int(det.box.y2)

        # Box
        cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), color, 2)

        if draw_labels:
            label = f"{det.label} {det.score * 100:.0f}%"
            font = cv2.FONT_HERSHEY_SIMPLEX
            scale = 0.5
            thickness = 1
            (tw, th), baseline = cv2.getTextSize(
                label, font, scale, thickness,
            )
            # Label background
            ly = max(y1 - th - 8, 0)
            cv2.rectangle(
                frame_bgr,
                (x1, ly),
                (x1 + tw + 8, ly + th + 8),
                color,
                -1,
            )
            # Label text
            cv2.putText(
                frame_bgr,
                label,
                (x1 + 4, ly + th + 4),
                font,
                scale,
                (255, 255, 255),
                thickness,
                cv2.LINE_AA,
            )
    return frame_bgr


def _blur_faces_on_frame(
    frame_bgr: np.ndarray,
    privacy_engine,
    mode: str = "blur",
) -> tuple[np.ndarray, int]:
    """Detect and blur/pixelate faces on a BGR frame.

    Returns (modified_frame, face_count).
    """
    if privacy_engine is None or not privacy_engine.loaded:
        return frame_bgr, 0

    # Convert to PIL for the privacy engine
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)

    try:
        faces = privacy_engine.predict_faces(pil)
    except Exception:
        return frame_bgr, 0

    if not faces:
        return frame_bgr, 0

    from app.inference.privacy import anonymize_faces
    out_pil, count = anonymize_faces(pil, faces, mode=mode)

    # Convert back to BGR
    out_bgr = cv2.cvtColor(
        np.asarray(out_pil), cv2.COLOR_RGB2BGR,
    )
    return out_bgr, count


# ------------------------------------------------------------------
# H.264 re-encoding
# ------------------------------------------------------------------

def _reencode_to_h264(src: Path) -> Path:
    """Re-encode *src* to H.264/AAC MP4 via ffmpeg (browser-safe).

    Returns a new path.  The original file is deleted on success.
    """
    dst = src.with_suffix(".h264.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",               # drop audio (we don't need it)
        str(dst),
    ]
    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            timeout=600,
        )
        src.unlink(missing_ok=True)
        return dst
    except FileNotFoundError:
        logger.warning(
            "ffmpeg not found – serving raw mp4v (may not play in browser)",
        )
        return src
    except subprocess.CalledProcessError as exc:
        logger.warning("ffmpeg re-encode failed: %s", exc.stderr[:500])
        return src


# ------------------------------------------------------------------
# Main render function
# ------------------------------------------------------------------

def render_annotated_video(
    source_path: Path,
    frame_results: list[dict],
    *,
    draw_boxes: bool = True,
    draw_labels: bool = True,
    apply_privacy: bool = True,
    frame_interval: int = 1,
) -> Path:
    """Render an annotated MP4 from source video + detection results.

    Parameters
    ----------
    source_path : Path
        Original video file.
    frame_results : list[dict]
        List of ``{frame_index, detections}`` from a VideoInferResponse.
    draw_boxes : bool
        Draw bounding boxes on detected objects.
    draw_labels : bool
        Draw labels + scores on boxes (only if *draw_boxes* is True).
    apply_privacy : bool
        Apply face blur/pixelate per frame.
    frame_interval : int
        Which frames were analysed (for index matching).

    Returns
    -------
    Path
        Path to the rendered MP4 file (H.264 if ffmpeg is available).
    """

    cap = cv2.VideoCapture(str(source_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {source_path}")

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0

    # ---- Build detection lookup ----
    frame_det_map: dict[int, list[Detection]] = {}
    for fr in frame_results:
        idx = fr.get("frame_index", -1)
        raw_dets = fr.get("detections", [])
        dets: list[Detection] = []
        for d in raw_dets:
            if isinstance(d, Detection):
                dets.append(d)
            elif isinstance(d, dict):
                dets.append(Detection(
                    class_id=d.get("class_id", 0),
                    label=d.get("label", ""),
                    score=d.get("score", 0),
                    box=Box(**(d.get("box", {}))),
                ))
        frame_det_map[idx] = dets

    # ---- Interpolate detections for smooth playback ----
    if draw_boxes and total_frames > 0:
        interp_map = _build_interpolated_detections(
            frame_det_map, total_frames,
        )
    else:
        interp_map = frame_det_map

    # ---- Privacy engine (lazy init) ----
    privacy_engine = None
    privacy_mode = "blur"
    if apply_privacy:
        try:
            from app.inference.privacy import (
                get_privacy_engine,
                privacy_enabled,
            )
            if privacy_enabled():
                privacy_engine = get_privacy_engine()
                privacy_mode = os.getenv(
                    "VISION_PRIVACY_MODE", "blur",
                ).strip().lower()
        except Exception:
            pass

    # ---- Write frames ----
    out_path = Path(tempfile.mktemp(
        suffix=".mp4", prefix="vision_render_",
    ))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))

    frame_idx = 0
    while True:
        ok, bgr = cap.read()
        if not ok:
            break

        # Apply privacy blur on every frame (not just sampled)
        if apply_privacy and privacy_engine is not None:
            bgr, _ = _blur_faces_on_frame(
                bgr, privacy_engine, privacy_mode,
            )

        # Draw boxes (now available for ALL frames via interpolation)
        if draw_boxes and frame_idx in interp_map:
            dets = interp_map[frame_idx]
            if dets:
                bgr = _draw_boxes_on_frame(
                    bgr, dets, draw_labels=draw_labels,
                )

        writer.write(bgr)
        frame_idx += 1

    cap.release()
    writer.release()

    logger.info(
        "video_rendered frames=%d output=%s",
        frame_idx, out_path.name,
    )

    # ---- Re-encode to H.264 for browser compatibility ----
    final = _reencode_to_h264(out_path)
    logger.info("video_final output=%s", final.name)
    return final
