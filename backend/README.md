# Backend (FastAPI Runner)

CPU-first inference service using ONNX Runtime.

## Quick start (Windows PowerShell)

1) Create venv and install deps:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) (Optional) set model path:

```powershell
$env:VISION_MODEL_PATH = "..\models\demo\v1\model.onnx"
```

3) Run API:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger UI: http://localhost:8000/docs

## Model bundle contract

The backend expects a model bundle folder like:

- `models/<name>/<version>/model.onnx`
- `models/<name>/<version>/labels.txt`
- `models/<name>/<version>/meta.json`

The ONNX should include NMS so outputs look like `[x1,y1,x2,y2,score,class]`.
If your ONNX exports raw predictions (no NMS), the server will return an error telling you how to export a compatible model.

## Privacy & Anonymization

Optional face anonymization before inference. Enable with `VISION_PRIVACY_FACE_BLUR=1` and provide a face detector bundle.

Env vars:
- `VISION_PRIVACY_MODEL_PATH`: path to privacy model bundle (model.onnx)
- `VISION_PRIVACY_MODE`: `blur` or `pixelate` (default: blur)
- `VISION_PRIVACY_MIN_SCORE`: min face score (default: 0.5)
- `VISION_PRIVACY_BLUR_RADIUS`: blur radius (default: 12)
- `VISION_PRIVACY_PIXELATE_SIZE`: pixel block size (default: 10)

Smoke test script:

```powershell
python .\scripts\privacy_smoke_test.py --image ..\input\test.jpg --model ..\models\privacy\v1\model.onnx
```
