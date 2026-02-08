from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnxruntime as ort  # type: ignore
from PIL import Image, ImageFilter

from app.inference.ort import get_ort_providers_from_env
from app.inference.preprocess import letterbox


_ULFD_MIN_BOXES = [[10, 16, 24], [32, 48], [64, 96], [128, 192, 256]]
_ULFD_STRIDES = [8, 16, 32, 64]
_ULFD_VARIANCE = (0.1, 0.2)


@dataclass
class FaceBox:
    x1: float
    y1: float
    x2: float
    y2: float
    score: float


class PrivacyEngine:
    def __init__(self) -> None:
        self._session: ort.InferenceSession | None = None
        self._input_name: str | None = None
        self._input_size: tuple[int, int] | None = None  # (w,h)
        self._configured_model_path: str | None = None
        self._detail: str | None = None
        self._output_names: list[str] = []
        self._use_letterbox: bool = True
        self._is_ulfd: bool = False
        self._min_score: float = float(
            os.getenv("VISION_PRIVACY_MIN_SCORE", "0.5")
        )

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
        model_path = os.getenv("VISION_PRIVACY_MODEL_PATH")
        if not model_path:
            self._configured_model_path = None
            self._detail = (
                "Set VISION_PRIVACY_MODEL_PATH"
                " to <bundle>/model.onnx"
            )
            return

        model_file = Path(model_path)
        if model_file.is_dir():
            model_file = model_file / "model.onnx"

        self._configured_model_path = str(model_file)

        if not model_file.exists():
            self._detail = f"Privacy model file not found: {model_file}"
            return

        meta_file = model_file.parent / "meta.json"
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
            raise RuntimeError("ONNX privacy model has no inputs")

        self._input_name = inputs[0].name
        self._output_names = [o.name for o in self._session.get_outputs()]
        shape = inputs[0].shape

        if (
            self._input_size is None
            and isinstance(shape, list)
            and len(shape) == 4
        ):
            h = shape[2] if isinstance(shape[2], int) else None
            w = shape[3] if isinstance(shape[3], int) else None
            if h and w:
                self._input_size = (int(w), int(h))

        if self._input_size is None:
            self._input_size = (640, 640)

        raw_letterbox = os.getenv("VISION_PRIVACY_LETTERBOX")
        if raw_letterbox is None or not raw_letterbox.strip():
            self._use_letterbox = self._input_size[0] == self._input_size[1]
        else:
            self._use_letterbox = _truthy(raw_letterbox)

        self._is_ulfd = (
            _looks_like_ulfd_names(self._output_names)
            or "ulfd" in str(model_file).lower()
        )

        # ULFD models produce lower confidence scores; use a lower default
        # unless the user explicitly set VISION_PRIVACY_MIN_SCORE.
        if self._is_ulfd and not os.getenv("VISION_PRIVACY_MIN_SCORE"):
            self._min_score = 0.15

        self._detail = (
            f"Loaded privacy model. input_size={self._input_size} "
            f"ulfd={self._is_ulfd} providers={providers}"
        )

    def predict_faces(self, image: Image.Image) -> list[FaceBox]:
        if not self._session or not self._input_name:
            raise RuntimeError("Privacy engine not loaded")

        in_w, in_h = self._input_size or (640, 640)
        if self._use_letterbox:
            resized, ratio, (pad_x, pad_y) = letterbox(image, (in_w, in_h))
            scale_x = 1.0 / ratio
            scale_y = 1.0 / ratio
            offset_x = pad_x
            offset_y = pad_y
        else:
            resized = image.resize((in_w, in_h), resample=Image.BILINEAR)
            scale_x = image.width / in_w
            scale_y = image.height / in_h
            offset_x = 0.0
            offset_y = 0.0

        arr = np.asarray(resized).astype(np.float32)
        if self._is_ulfd:
            arr = (arr - 127.0) / 128.0
        else:
            arr = arr / 255.0
        arr = np.transpose(arr, (2, 0, 1))
        arr = np.expand_dims(arr, axis=0)

        outputs = self._session.run(None, {self._input_name: arr})
        if not outputs:
            return []

        faces = self._parse_outputs(outputs)

        mapped: list[FaceBox] = []
        for face in faces:
            x1 = (face.x1 - offset_x) * scale_x
            x2 = (face.x2 - offset_x) * scale_x
            y1 = (face.y1 - offset_y) * scale_y
            y2 = (face.y2 - offset_y) * scale_y

            x1 = float(max(0.0, min(x1, image.width)))
            x2 = float(max(0.0, min(x2, image.width)))
            y1 = float(max(0.0, min(y1, image.height)))
            y2 = float(max(0.0, min(y2, image.height)))

            if face.score < self._min_score:
                continue

            mapped.append(
                FaceBox(
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    score=face.score,
                )
            )

        return mapped

    def _parse_outputs(self, outputs: list[np.ndarray]) -> list[FaceBox]:
        if _looks_like_ulfd(outputs, self._output_names):
            return _decode_ulfd(
                outputs,
                self._output_names,
                self._input_size,
                self._min_score,
            )

        arr = np.asarray(outputs[0])

        if arr.ndim == 3 and arr.shape[0] == 1:
            arr = arr[0]

        if arr.ndim == 2 and arr.shape[1] >= 6:
            faces: list[FaceBox] = []
            for row in arr:
                score = float(row[4])
                if score <= 0:
                    continue
                faces.append(
                    FaceBox(
                        x1=float(row[0]),
                        y1=float(row[1]),
                        x2=float(row[2]),
                        y2=float(row[3]),
                        score=score,
                    )
                )
            return faces

        if arr.ndim == 2 and arr.shape[1] == 5:
            faces = []
            for row in arr:
                score = float(row[4])
                if score <= 0:
                    continue
                faces.append(
                    FaceBox(
                        x1=float(row[0]),
                        y1=float(row[1]),
                        x2=float(row[2]),
                        y2=float(row[3]),
                        score=score,
                    )
                )
            return faces

        if arr.ndim == 2 and arr.shape[1] == 4:
            faces = []
            for row in arr:
                faces.append(
                    FaceBox(
                        x1=float(row[0]),
                        y1=float(row[1]),
                        x2=float(row[2]),
                        y2=float(row[3]),
                        score=1.0,
                    )
                )
            return faces

        raise ValueError(
            "Unsupported privacy model output format. "
            "Expected (N,6), (N,5), or (N,4) style outputs."
        )


def _looks_like_ulfd_names(output_names: list[str]) -> bool:
    """Check if output names suggest a ULFD-style model (boxes + scores)."""
    has_boxes = any("boxes" in n.lower() for n in output_names)
    has_scores = any(
        "scores" in n.lower() or "conf" in n.lower() for n in output_names
    )
    return has_boxes and has_scores and len(output_names) >= 2


def _looks_like_ulfd(
    outputs: list[np.ndarray],
    output_names: list[str],
) -> bool:
    return _select_ulfd_tensors(outputs, output_names) is not None


def _decode_ulfd(
    outputs: list[np.ndarray],
    output_names: list[str],
    input_size: tuple[int, int] | None,
    min_score: float,
) -> list[FaceBox]:
    in_w, in_h = input_size or (320, 320)

    selected = _select_ulfd_tensors(outputs, output_names)
    if selected is None:
        raise ValueError("ULFD outputs not found")

    boxes, scores = selected

    if boxes.ndim == 3 and boxes.shape[0] == 1:
        boxes = boxes[0]
    if scores.ndim == 3 and scores.shape[0] == 1:
        scores = scores[0]

    priors = _ulfd_priors(in_w, in_h)
    needs_prior_decode = priors.shape[0] == boxes.shape[0]

    if needs_prior_decode:

        cxcy = priors[:, 0:2]
        wh = priors[:, 2:4]

        var0, var1 = _ULFD_VARIANCE
        decoded_cxcy = cxcy + boxes[:, 0:2] * var0 * wh
        decoded_wh = wh * np.exp(boxes[:, 2:4] * var1)

        decoded = np.zeros_like(boxes)
        decoded[:, 0:2] = decoded_cxcy - decoded_wh / 2
        decoded[:, 2:4] = decoded_cxcy + decoded_wh / 2
        boxes = decoded

    scores = scores[:, 1]
    keep = scores >= min_score
    boxes = boxes[keep]
    scores = scores[keep]

    if boxes.size == 0:
        return []

    if boxes.size > 0:
        max_val = float(np.max(boxes))
        min_val = float(np.min(boxes))
        if max_val <= 1.5 and min_val >= -0.5:
            boxes[:, 0] = boxes[:, 0] * in_w
            boxes[:, 2] = boxes[:, 2] * in_w
            boxes[:, 1] = boxes[:, 1] * in_h
            boxes[:, 3] = boxes[:, 3] * in_h

    boxes = _choose_ulfd_box_format(boxes, in_w, in_h)

    order = scores.argsort()[::-1]
    boxes = boxes[order]
    scores = scores[order]

    iou_thresh = float(os.getenv("VISION_PRIVACY_NMS_IOU", "0.3"))
    keep_idx = _nms(boxes, scores, iou_thresh)

    faces: list[FaceBox] = []
    for idx in keep_idx:
        b = boxes[idx]
        faces.append(
            FaceBox(
                x1=float(b[0]),
                y1=float(b[1]),
                x2=float(b[2]),
                y2=float(b[3]),
                score=float(scores[idx]),
            )
        )

    return faces


def _choose_ulfd_box_format(
    boxes: np.ndarray,
    in_w: int,
    in_h: int,
) -> np.ndarray:
    if boxes.size == 0:
        return boxes

    corners = boxes
    center = _cxcywh_to_xyxy(boxes)

    score_corners = _count_valid_boxes(corners, in_w, in_h)
    score_center = _count_valid_boxes(center, in_w, in_h)

    return center if score_center > score_corners else corners


def _cxcywh_to_xyxy(boxes: np.ndarray) -> np.ndarray:
    out = boxes.copy()
    out[:, 0] = boxes[:, 0] - boxes[:, 2] / 2
    out[:, 1] = boxes[:, 1] - boxes[:, 3] / 2
    out[:, 2] = boxes[:, 0] + boxes[:, 2] / 2
    out[:, 3] = boxes[:, 1] + boxes[:, 3] / 2
    return out


def _count_valid_boxes(boxes: np.ndarray, in_w: int, in_h: int) -> int:
    if boxes.size == 0:
        return 0

    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]

    w = x2 - x1
    h = y2 - y1

    valid = (
        (w > 1.0)
        & (h > 1.0)
        & (x2 > 0.0)
        & (y2 > 0.0)
        & (x1 < float(in_w))
        & (y1 < float(in_h))
    )
    return int(np.sum(valid))


def _select_ulfd_tensors(
    outputs: list[np.ndarray],
    output_names: list[str],
) -> tuple[np.ndarray, np.ndarray] | None:
    if len(outputs) < 2:
        return None

    boxes_idx = None
    scores_idx = None

    for idx, name in enumerate(output_names):
        lname = name.lower()
        if boxes_idx is None and "boxes" in lname:
            boxes_idx = idx
        if scores_idx is None and ("scores" in lname or "conf" in lname):
            scores_idx = idx

    for idx, arr in enumerate(outputs):
        a = np.asarray(arr)
        if a.ndim == 3 and a.shape[0] == 1:
            a = a[0]
        if a.ndim == 2 and a.shape[1] == 4 and boxes_idx is None:
            boxes_idx = idx
        if a.ndim == 2 and a.shape[1] >= 2 and scores_idx is None:
            scores_idx = idx

    if boxes_idx is None or scores_idx is None:
        return None

    return np.asarray(outputs[boxes_idx]), np.asarray(outputs[scores_idx])


def _ulfd_priors(in_w: int, in_h: int) -> np.ndarray:
    feature_maps = [
        (int(np.ceil(in_w / step)), int(np.ceil(in_h / step)))
        for step in _ULFD_STRIDES
    ]

    priors: list[list[float]] = []
    for idx, (fm_w, fm_h) in enumerate(feature_maps):
        min_boxes = _ULFD_MIN_BOXES[idx]
        step = _ULFD_STRIDES[idx]
        for y in range(fm_h):
            for x in range(fm_w):
                cx = (x + 0.5) * step / in_w
                cy = (y + 0.5) * step / in_h
                for mb in min_boxes:
                    w = mb / in_w
                    h = mb / in_h
                    priors.append([cx, cy, w, h])

    return np.asarray(priors, dtype=np.float32)


def _nms(
    boxes: np.ndarray,
    scores: np.ndarray,
    iou_thresh: float,
) -> list[int]:
    if boxes.size == 0:
        return []

    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]

    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]

    keep: list[int] = []
    while order.size > 0:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h

        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        inds = np.where(iou <= iou_thresh)[0]
        order = order[inds + 1]

    return keep


def privacy_enabled() -> bool:
    return os.getenv("VISION_PRIVACY_FACE_BLUR", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def anonymize_faces(
    image: Image.Image,
    faces: list[FaceBox],
    mode: str = "blur",
) -> tuple[Image.Image, int]:
    if not faces:
        return image, 0

    out = image.copy()
    applied = 0

    blur_radius = float(os.getenv("VISION_PRIVACY_BLUR_RADIUS", "12"))
    pixelate_size = int(os.getenv("VISION_PRIVACY_PIXELATE_SIZE", "10"))

    for face in faces:
        x1 = int(max(0, round(face.x1)))
        y1 = int(max(0, round(face.y1)))
        x2 = int(min(out.width, round(face.x2)))
        y2 = int(min(out.height, round(face.y2)))

        if x2 <= x1 or y2 <= y1:
            continue

        region = out.crop((x1, y1, x2, y2))
        if mode == "pixelate":
            region = _pixelate_region(region, pixelate_size)
        else:
            region = region.filter(ImageFilter.GaussianBlur(blur_radius))

        out.paste(region, (x1, y1))
        applied += 1

    return out, applied


def _pixelate_region(region: Image.Image, block_size: int) -> Image.Image:
    if block_size <= 1:
        return region

    w, h = region.size
    w_small = max(1, w // block_size)
    h_small = max(1, h // block_size)

    small = region.resize((w_small, h_small), resample=Image.NEAREST)
    return small.resize((w, h), resample=Image.NEAREST)


_PRIVACY_ENGINE: PrivacyEngine | None = None


def get_privacy_engine() -> PrivacyEngine:
    global _PRIVACY_ENGINE
    if _PRIVACY_ENGINE is None:
        _PRIVACY_ENGINE = PrivacyEngine()
    return _PRIVACY_ENGINE


def reset_privacy_engine() -> None:
    global _PRIVACY_ENGINE
    _PRIVACY_ENGINE = None
