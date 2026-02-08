from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnxruntime as ort  # type: ignore
from PIL import Image

from app.api.schema import Box, Detection
from app.inference.preprocess import letterbox
from app.inference.ort import get_ort_providers_from_env


@dataclass
class EngineState:
    configured_model_path: str | None
    loaded: bool
    detail: str | None


class OnnxYoloEngine:
    def __init__(self) -> None:
        self._session: ort.InferenceSession | None = None
        self._input_name: str | None = None
        self._labels: list[str] = []
        self._input_size: tuple[int, int] | None = None  # (w,h)
        self._configured_model_path: str | None = None
        self._detail: str | None = None

        self._configure_from_env()

    @property
    def configured_model_path(self) -> str | None:
        return self._configured_model_path

    @property
    def loaded(self) -> bool:
        return self._session is not None

    @property
    def detail(self) -> str | None:
        return self._detail

    def _configure_from_env(self) -> None:
        model_path = os.getenv("VISION_MODEL_PATH")
        if not model_path:
            self._configured_model_path = None
            self._detail = "Set VISION_MODEL_PATH to <bundle>/model.onnx"
            return

        model_file = Path(model_path)
        if model_file.is_dir():
            model_file = model_file / "model.onnx"

        self._configured_model_path = str(model_file)

        if not model_file.exists():
            self._detail = f"Model file not found: {model_file}"
            return

        bundle_dir = model_file.parent
        labels_file = bundle_dir / "labels.txt"
        meta_file = bundle_dir / "meta.json"

        if labels_file.exists():
            self._labels = [
                line.strip()
                for line in labels_file.read_text(encoding="utf-8")
                .splitlines()
                if line.strip()
            ]
        else:
            self._labels = []

        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                size = meta.get("input_size")
                if isinstance(size, list) and len(size) == 2:
                    self._input_size = (int(size[0]), int(size[1]))
            except Exception:  # noqa: BLE001
                pass

        self._load_session(model_file)

    def _load_session(self, model_file: Path) -> None:
        sess_opts = ort.SessionOptions()

        providers, provider_options, uses_openvino = (
            get_ort_providers_from_env()
        )

        # OpenVINO EP docs recommend disabling ORT graph-level optimizations.
        sess_opts.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_DISABLE_ALL
            if uses_openvino
            else ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )

        self._session = ort.InferenceSession(
            str(model_file),
            sess_options=sess_opts,
            providers=providers,
            provider_options=provider_options,
        )

        inputs = self._session.get_inputs()
        if not inputs:
            raise RuntimeError("ONNX model has no inputs")

        self._input_name = inputs[0].name
        shape = inputs[0].shape

        # If meta.json didn't specify size,
        # try to infer from static ONNX input.
        if (
            self._input_size is None
            and isinstance(shape, list)
            and len(shape) == 4
        ):
            # Common: (1,3,H,W) or (1,H,W,3)
            h = shape[2] if isinstance(shape[2], int) else None
            w = shape[3] if isinstance(shape[3], int) else None
            if h and w:
                self._input_size = (int(w), int(h))

        if self._input_size is None:
            # Default to common YOLO size; user should set meta.json.
            self._input_size = (640, 640)

        self._detail = (
            f"Loaded ONNX model. input_size={self._input_size} "
            f"labels={len(self._labels)} providers={providers}"
        )

    def predict(self, image: Image.Image) -> list[Detection]:
        if not self._session or not self._input_name:
            raise RuntimeError("Engine not loaded")

        in_w, in_h = self._input_size or (640, 640)
        resized, ratio, (pad_x, pad_y) = letterbox(image, (in_w, in_h))

        arr = np.asarray(resized).astype(np.float32) / 255.0
        # NCHW
        arr = np.transpose(arr, (2, 0, 1))
        arr = np.expand_dims(arr, axis=0)

        outputs = self._session.run(None, {self._input_name: arr})
        if not outputs:
            return []

        dets = self._parse_outputs(outputs)

        # Map boxes back to original image pixels.
        mapped: list[Detection] = []
        for det in dets:
            x1, y1, x2, y2 = det[0], det[1], det[2], det[3]

            # Undo padding and scaling.
            x1 = (x1 - pad_x) / ratio
            x2 = (x2 - pad_x) / ratio
            y1 = (y1 - pad_y) / ratio
            y2 = (y2 - pad_y) / ratio

            # Clamp.
            x1 = float(max(0.0, min(x1, image.width)))
            x2 = float(max(0.0, min(x2, image.width)))
            y1 = float(max(0.0, min(y1, image.height)))
            y2 = float(max(0.0, min(y2, image.height)))

            score = float(det[4])
            class_id = int(det[5])
            if 0 <= class_id < len(self._labels):
                label = self._labels[class_id]
            else:
                label = str(class_id)

            mapped.append(
                Detection(
                    class_id=class_id,
                    label=label,
                    score=score,
                    box=Box(x1=x1, y1=y1, x2=x2, y2=y2),
                )
            )

        return mapped

    def _parse_outputs(self, outputs: list[np.ndarray]) -> list[list[float]]:
        """Return list of [x1,y1,x2,y2,score,class_id].

        This intentionally supports only "NMS-in-graph" ONNX exports
        for the MVP.
        """

        out0 = outputs[0]
        arr = np.asarray(out0)

        # Common "NMS-in-graph" shapes:
        # - (1, N, 6)
        # - (N, 6)
        # Where each row: x1,y1,x2,y2,score,class
        if arr.ndim == 3 and arr.shape[0] == 1:
            arr = arr[0]
        if arr.ndim == 2 and arr.shape[1] >= 6:
            rows = arr
            parsed: list[list[float]] = []
            for r in rows:
                x1 = float(r[0])
                y1 = float(r[1])
                x2 = float(r[2])
                y2 = float(r[3])
                score = float(r[4])
                cls = float(r[5])
                if score <= 0:
                    continue
                parsed.append([x1, y1, x2, y2, score, cls])
            return parsed

        raise ValueError(
            "Unsupported ONNX output format. For the MVP, export YOLO "
            "with NMS in the graph. "
            "If you are using Ultralytics: "
            "`yolo export model=yolov8n.pt format=onnx nms=True` "
            "and point VISION_MODEL_PATH at the bundle."
        )


_ENGINE: OnnxYoloEngine | None = None


def get_engine() -> OnnxYoloEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = OnnxYoloEngine()
    return _ENGINE


def reset_engine() -> None:
    global _ENGINE
    _ENGINE = None
