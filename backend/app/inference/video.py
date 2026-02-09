"""Video frame extraction using OpenCV.

Supports MP4, AVI, MOV, MKV, WebM.
"""

from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

import cv2
from PIL import Image

logger = logging.getLogger("vision.video")

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def is_video_file(path: Path) -> bool:
    """Return True if the path looks like a supported video file."""
    return path.suffix.lower() in VIDEO_EXTENSIONS


@dataclass
class FrameInfo:
    """Metadata about a single extracted frame."""

    index: int  # 0-based frame index in the *original* video
    timestamp_ms: float  # Position in milliseconds


@dataclass
class VideoMeta:
    """Metadata about the source video."""

    width: int
    height: int
    fps: float
    total_frames: int
    duration_ms: float
    codec: str


class VideoFrameExtractor:
    """Extract frames from a video file via OpenCV.

    Parameters
    ----------
    path : Path | str
        Path to the video file.
    frame_interval : int
        Extract every N-th frame.  1 = every frame.
    max_frames : int
        Hard cap on number of extracted frames (0 = unlimited).
    fps_target : float
        If > 0 use this as the target FPS for sampling
        (overrides frame_interval).
    """

    def __init__(
        self,
        path: Path | str,
        *,
        frame_interval: int = 1,
        max_frames: int = 0,
        fps_target: float = 0.0,
    ) -> None:
        self._path = Path(path)
        self._frame_interval = max(1, frame_interval)
        self._max_frames = max_frames
        self._fps_target = fps_target
        self._cap: cv2.VideoCapture | None = None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def open(self) -> VideoMeta:
        """Open the video and return metadata."""
        cap = cv2.VideoCapture(str(self._path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {self._path}")
        self._cap = cap

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_ms = (total / fps) * 1000 if fps > 0 else 0.0
        fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec = (
            "".join(chr((fourcc >> 8 * i) & 0xFF) for i in range(4))
            if fourcc
            else "unknown"
        )

        # If fps_target is set, compute the frame_interval from it.
        if self._fps_target > 0 and fps > 0:
            self._frame_interval = max(1, round(fps / self._fps_target))

        logger.info(
            "video_opened path=%s width=%d height=%d fps=%.2f total=%d "
            "interval=%d max=%d",
            self._path.name,
            w,
            h,
            fps,
            total,
            self._frame_interval,
            self._max_frames,
        )

        return VideoMeta(
            width=w,
            height=h,
            fps=fps,
            total_frames=total,
            duration_ms=duration_ms,
            codec=codec,
        )

    def extract_frames(self):
        """Yield (FrameInfo, PIL.Image) tuples.

        The generator honours frame_interval and max_frames.
        """
        if self._cap is None:
            raise RuntimeError("Call open() first")

        cap = self._cap
        idx = 0
        yielded = 0

        while True:
            ok, bgr = cap.read()
            if not ok:
                break

            if idx % self._frame_interval == 0:
                ts = cap.get(cv2.CAP_PROP_POS_MSEC)
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                pil = Image.fromarray(rgb)
                yield FrameInfo(index=idx, timestamp_ms=ts), pil
                yielded += 1

                if 0 < self._max_frames <= yielded:
                    break

            idx += 1

        logger.info(
            "video_extracted frames=%d from=%s",
            yielded,
            self._path.name,
        )

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    # shortcuts
    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *_exc):
        self.close()


def save_temp_upload(data: bytes, suffix: str = ".mp4") -> Path:
    """Write uploaded video bytes to a temp file and return the path."""
    tmp = tempfile.NamedTemporaryFile(
        delete=False, suffix=suffix, prefix="vision_video_"
    )
    tmp.write(data)
    tmp.close()
    return Path(tmp.name)
