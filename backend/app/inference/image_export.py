"""Annotate images with bounding boxes and optional privacy blur.

Provides a reusable ``ImageAnnotator`` that draws detection bounding
boxes + labels on a PIL image.  Used by the image export endpoints
and the watch-folder annotated output mode.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

from app.api.schema import Detection

logger = logging.getLogger("vision.image.export")

# Volvo Cars palette (same as frontend / video_render)
COLORS = [
    "#003057",
    "#d36000",
    "#1a8754",
    "#4a9eff",
    "#c41230",
    "#004d8c",
    "#ff8533",
    "#2ecc71",
    "#6db3ff",
    "#e74c3c",
]


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert a hex colour string to an (R, G, B) tuple."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _get_font(size: int = 14) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a TrueType font, fall back to the built-in bitmap font."""
    # Common paths where a decent font might exist
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


@dataclass
class AnnotationStyle:
    """Configuration for how bounding boxes are drawn."""

    line_width: int = 3
    font_size: int = 14
    show_labels: bool = True
    show_scores: bool = True
    label_padding: int = 4


class ImageAnnotator:
    """Draw detection bounding boxes and labels onto PIL images."""

    def __init__(self, style: AnnotationStyle | None = None) -> None:
        self.style = style or AnnotationStyle()
        self._font = _get_font(self.style.font_size)

    def annotate(
        self,
        image: Image.Image,
        detections: list[Detection],
        *,
        copy: bool = True,
    ) -> Image.Image:
        """Return *image* with bounding boxes drawn.

        Parameters
        ----------
        image:
            Source PIL image (RGB).
        detections:
            List of detections to draw.
        copy:
            If True (default), the original image is not modified.

        Returns
        -------
        PIL.Image.Image
            Annotated image.
        """
        if copy:
            image = image.copy()

        draw = ImageDraw.Draw(image)

        for idx, det in enumerate(detections):
            color = _hex_to_rgb(COLORS[idx % len(COLORS)])
            x1, y1 = int(det.box.x1), int(det.box.y1)
            x2, y2 = int(det.box.x2), int(det.box.y2)

            # Bounding box
            draw.rectangle(
                [x1, y1, x2, y2],
                outline=color,
                width=self.style.line_width,
            )

            # Semi-transparent fill
            overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle(
                [x1, y1, x2, y2],
                fill=(*color, 32),  # ~12% opacity
            )
            image = Image.alpha_composite(
                image.convert("RGBA"), overlay,
            ).convert("RGB")
            draw = ImageDraw.Draw(image)

            if self.style.show_labels:
                # Build label text
                parts = [det.label]
                if self.style.show_scores:
                    parts.append(f"{det.score * 100:.0f}%")
                label = " ".join(parts)

                pad = self.style.label_padding
                bbox = self._font.getbbox(label)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]

                label_y = max(0, y1 - th - pad * 2 - 2)

                # Label background
                draw.rectangle(
                    [x1, label_y, x1 + tw + pad * 2, label_y + th + pad * 2],
                    fill=color,
                )
                # Label text (white on coloured background)
                draw.text(
                    (x1 + pad, label_y + pad),
                    label,
                    fill=(255, 255, 255),
                    font=self._font,
                )

        return image

    def annotate_to_bytes(
        self,
        image: Image.Image,
        detections: list[Detection],
        *,
        format: str = "JPEG",
        quality: int = 90,
    ) -> bytes:
        """Annotate and return the result as encoded bytes."""
        result = self.annotate(image, detections)
        buf = io.BytesIO()
        if format.upper() == "PNG":
            result.save(buf, format="PNG")
        else:
            result.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()


# Module-level singleton for convenience
_ANNOTATOR: ImageAnnotator | None = None


def get_annotator(style: AnnotationStyle | None = None) -> ImageAnnotator:
    """Return a shared ``ImageAnnotator`` instance."""
    global _ANNOTATOR
    if _ANNOTATOR is None:
        _ANNOTATOR = ImageAnnotator(style)
    return _ANNOTATOR
