from __future__ import annotations

from PIL import Image


def letterbox(
  image: Image.Image,
  size: tuple[int, int],
) -> tuple[Image.Image, float, tuple[float, float]]:
    """Resize+pad to `size` while preserving aspect ratio.

    Returns: (resized_image, ratio, (pad_x, pad_y))

    Coordinates in the resized image can be mapped back to the original via:
      x' = (x - pad_x) / ratio
      y' = (y - pad_y) / ratio
    """

    target_w, target_h = size
    src_w, src_h = image.size

    ratio = min(target_w / src_w, target_h / src_h)
    new_w = int(round(src_w * ratio))
    new_h = int(round(src_h * ratio))

    resized = image.resize((new_w, new_h), resample=Image.BILINEAR)
    canvas = Image.new("RGB", (target_w, target_h), (114, 114, 114))

    pad_x = (target_w - new_w) / 2
    pad_y = (target_h - new_h) / 2

    canvas.paste(resized, (int(round(pad_x)), int(round(pad_y))))
    return canvas, float(ratio), (float(pad_x), float(pad_y))
