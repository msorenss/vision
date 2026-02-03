from __future__ import annotations

import io
import json
import os
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

from app.inference.engine import reset_engine


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _default_bundle_dir() -> Path:
    # Default to repo-local models folder if present; otherwise use ./models.
    here = Path(__file__).resolve()
    repo_root = here.parents[2]  # backend/
    models_dir = repo_root / "models"
    return models_dir / "standard" / "yolov8n" / "v1"


def bootstrap_model_if_needed() -> None:
    """Optionally ensure a standard model exists on disk.

    Controlled by env vars:

    - VISION_BOOTSTRAP=1 enables bootstrapping.
    - VISION_MODEL_PATH: where the runner loads the model from.
      If not set, it will be set to a default bundle location.
    - VISION_BOOTSTRAP_BUNDLE_URL: if set, download a zip bundle from here.
      The zip must contain: model.onnx, labels.txt, meta.json.
        - Otherwise, if `ultralytics` is installed,
            export yolov8n to ONNX (nms=True).

    This function is safe to call repeatedly.
    """

    if not _truthy(os.getenv("VISION_BOOTSTRAP")):
        return

    model_path = os.getenv("VISION_MODEL_PATH")
    if not model_path:
        bundle_dir = _default_bundle_dir()
        bundle_dir.mkdir(parents=True, exist_ok=True)
        model_path = str(bundle_dir / "model.onnx")
        os.environ["VISION_MODEL_PATH"] = model_path

    model_file = Path(model_path)
    if model_file.is_dir():
        model_file = model_file / "model.onnx"
        os.environ["VISION_MODEL_PATH"] = str(model_file)

    # If present, validate it can be loaded by the installed ONNX Runtime.
    # If it fails to load (e.g. unsupported opset), we will re-export/re-download.
    if model_file.exists():
        try:
            import onnxruntime as ort

            _ = ort.InferenceSession(
                str(model_file),
                providers=["CPUExecutionProvider"],
            )
            return
        except Exception:
            pass

    bundle_dir = model_file.parent
    bundle_dir.mkdir(parents=True, exist_ok=True)

    bundle_url = os.getenv("VISION_BOOTSTRAP_BUNDLE_URL")
    if bundle_url:
        _download_bundle_zip(bundle_url, bundle_dir)
        reset_engine()
        return

    # Fallback: use ultralytics if available.
    _export_ultralytics_standard_model(bundle_dir)
    reset_engine()


def _download_bundle_zip(url: str, out_dir: Path) -> None:
    req = Request(url, headers={"User-Agent": "vision-bootstrap/0.1"})
    with urlopen(req, timeout=120) as resp:  # noqa: S310
        if resp.status != 200:
            raise RuntimeError(f"Bundle download failed: HTTP {resp.status}")
        data = resp.read()

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(out_dir)

    _validate_bundle(out_dir)


def _export_ultralytics_standard_model(out_dir: Path) -> None:
    try:
        from ultralytics import YOLO  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "No model found and no VISION_BOOTSTRAP_BUNDLE_URL provided. "
            "Install ultralytics (and its deps) or provide a bundle URL."
        ) from exc

    imgsz = int(os.getenv("VISION_BOOTSTRAP_IMGSZ", "640"))
    base_model = os.getenv("VISION_BOOTSTRAP_MODEL", "yolov8n.pt")
    opset = int(os.getenv("VISION_BOOTSTRAP_OPSET", "20"))

    model = YOLO(base_model)
    exported = model.export(format="onnx", imgsz=imgsz, nms=True, opset=opset)

    exported_path = Path(str(exported)).resolve()
    (out_dir / "model.onnx").write_bytes(exported_path.read_bytes())

    names = model.names if hasattr(model, "names") else {}
    if isinstance(names, dict):
        labels = [names[i] for i in sorted(names.keys())]
    else:
        labels = []
    (out_dir / "labels.txt").write_text(
        "\n".join(labels) + "\n",
        encoding="utf-8",
    )

    meta = {
        "input_size": [imgsz, imgsz],
        "export": {"format": "onnx", "nms": True, "opset": opset},
        "source_model": base_model,
        "bootstrap": True,
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, indent=2) + "\n",
        encoding="utf-8",
    )

    _validate_bundle(out_dir)


def _validate_bundle(dir_path: Path) -> None:
    required = ["model.onnx", "labels.txt", "meta.json"]
    missing = [name for name in required if not (dir_path / name).exists()]
    if missing:
        missing_str = ", ".join(missing)
        raise RuntimeError(
            (
                f"Bootstrap bundle incomplete in {dir_path}. "
                f"Missing: {missing_str}"
            )
        )
