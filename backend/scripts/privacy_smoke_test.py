from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PIL import Image, ImageOps


def _ensure_app_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def _default_out_path(image_path: Path) -> Path:
    return image_path.with_name(f"{image_path.stem}.privacy.jpg")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run a privacy model on a single"
            " image and write an anonymized copy."
        ),
    )
    parser.add_argument("--image", required=True, help="Path to input image")
    parser.add_argument(
        "--model",
        help="Path to privacy model bundle (model.onnx) or directory",
    )
    parser.add_argument(
        "--out",
        help="Output image path (default: <input>.privacy.jpg)",
    )
    parser.add_argument(
        "--mode",
        choices=["blur", "pixelate"],
        default="blur",
        help="Anonymization mode",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.5,
        help="Minimum face score to anonymize",
    )
    parser.add_argument(
        "--blur-radius",
        type=float,
        default=12.0,
        help="Gaussian blur radius",
    )
    parser.add_argument(
        "--pixelate-size",
        type=int,
        default=10,
        help="Pixelation block size",
    )
    args = parser.parse_args()

    _ensure_app_on_path()

    if args.model:
        os.environ["VISION_PRIVACY_MODEL_PATH"] = args.model

    os.environ["VISION_PRIVACY_MIN_SCORE"] = str(args.min_score)
    os.environ["VISION_PRIVACY_BLUR_RADIUS"] = str(args.blur_radius)
    os.environ["VISION_PRIVACY_PIXELATE_SIZE"] = str(args.pixelate_size)

    from app.inference.privacy import PrivacyEngine, anonymize_faces

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        return 1

    model_path = os.getenv("VISION_PRIVACY_MODEL_PATH")
    if not model_path:
        print("Set --model or VISION_PRIVACY_MODEL_PATH before running.")
        return 1

    try:
        pil = ImageOps.exif_transpose(Image.open(image_path)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        print(f"Invalid image: {exc}")
        return 1

    engine = PrivacyEngine()
    if not engine.loaded:
        detail = engine.detail or "Privacy model failed to load"
        print(detail)
        return 1

    faces = engine.predict_faces(pil)
    out, applied = anonymize_faces(pil, faces, mode=args.mode)

    out_path = Path(args.out) if args.out else _default_out_path(image_path)
    out.save(out_path)

    print(f"Faces detected: {len(faces)}")
    print(f"Faces anonymized: {applied}")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
