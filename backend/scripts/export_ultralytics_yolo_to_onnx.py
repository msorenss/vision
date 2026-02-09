from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export an Ultralytics YOLO model to an"
            " ONNX bundle usable by the CPU Runner."
        )
    )
    parser.add_argument(
        "--model",
        default="yolov8n.pt",
        help="Ultralytics model path or name (default: yolov8n.pt)",
    )
    parser.add_argument(
        "--out",
        default=str(Path("..") / "models" / "demo" / "v1"),
        help="Output bundle directory (default: ../models/demo/v1)",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Input image size for export (default: 640)",
    )
    parser.add_argument(
        "--opset",
        type=int,
        default=20,
        help="ONNX opset version for export (default: 20)",
    )
    args = parser.parse_args()

    # Lazy import so the Runner doesn't require ultralytics.
    from ultralytics import YOLO  # type: ignore

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    model = YOLO(args.model)

    # Export with NMS in graph so the Runner can parse outputs easily.
    exported = model.export(
        format="onnx", imgsz=args.imgsz,
        nms=True, opset=args.opset,
    )

    # Ultralytics returns a path-like; copy/move into bundle.
    exported_path = Path(str(exported)).resolve()
    target = out_dir / "model.onnx"
    target.write_bytes(exported_path.read_bytes())

    # labels.txt
    names = model.names if hasattr(model, "names") else {}
    labels = (
        [names[i] for i in sorted(names.keys())]
        if isinstance(names, dict) else []
    )
    (out_dir / "labels.txt").write_text(
        "\n".join(labels) + "\n",
        encoding="utf-8",
    )

    # meta.json
    meta = {
        "input_size": [args.imgsz, args.imgsz],
        "export": {"format": "onnx", "nms": True, "opset": args.opset},
        "source_model": args.model,
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote bundle: {out_dir}")
    print(f"- model: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
