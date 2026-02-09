# Changelog

## v1.5.0 — 2026-02-09

### Features

#### Video Inference (P13)
- **Video upload & async inference** — `POST /api/v1/infer/video` accepts MP4, AVI, MOV, MKV, WebM
- **SSE progress streaming** — `GET /api/v1/infer/video/status/{job_id}`
- **Per-frame detection results** — `GET /api/v1/infer/video/result/{job_id}`
- **Frame extraction** — `VideoFrameExtractor` with configurable interval and max frames
- **Privacy per frame** — face anonymization applied before inference on each frame
- **Detection filters on video** — `filter_name` query parameter for video endpoint
- **Watch folder video support** — auto-process video files with JSON output

#### Annotated Video Export
- **Render annotated video** — `POST /api/v1/infer/video/export/{job_id}` with bounding boxes, labels, privacy blur
- **Smooth interpolation** — IoU-based greedy matching + linear interpolation between key-frames (no flicker)
- **H.264 re-encoding** — ffmpeg subprocess for browser-compatible MP4 (yuv420p + faststart)
- **Preview endpoint** — `GET /api/v1/infer/video/preview/{job_id}` with HTTP range support
- **Download endpoint** — `GET /api/v1/infer/video/export/{job_id}` for rendered video

#### Video Frontend
- **Video page** (`/video`) with drag-and-drop upload, SSE progress, frame navigator
- **Video player** — `<video>` element for annotated video preview
- **Export controls** — checkboxes for boxes, labels, privacy; render + download buttons
- **Filter selector** — same filter dropdown as image page, top-right of title row
- **i18n** — 32 video keys across 7 languages (sv, en, nl, sk, zh, fr, es)

#### Integrations
- **OPC UA / MQTT / Webhook for video** — video inference now pushes results to all configured integrations
- **Fix**: main event loop passed to thread-pool worker for reliable `asyncio.run_coroutine_threadsafe()` dispatch

### Fixes
- Fixed all Python lint errors (E501 line-too-long) across 9 backend files
- Removed unused `shutil` import in `video_render.py`
- Fixed comment spacing in color palette (`video_render.py`)
- Silenced TypeScript `baseUrl` deprecation warning (`ignoreDeprecations: "5.0"`)

### Docker
- Images: `marcussorensson218/vision-runner:1.5.0`, `vision-ui:1.5.0`, `vision-mcp:1.5.0`
- **ffmpeg** added to runner image (H.264 video encoding)
- **opencv-python-headless** added to requirements (video frame extraction)
- New environment variables:
  - `VISION_VIDEO_FRAME_INTERVAL` — sample every Nth frame (default: 5)
  - `VISION_VIDEO_MAX_FRAMES` — max frames to process (default: 300)

### Roadmap
- **P13** ✅ Video Mode — Done
- **P15** 🔄 Video-export — Done (image-export still open)
- **P14** 📋 Valbar Detektionsfunktion (multi-model)

---

## v1.4.3 — 2026-02-08

### Improvements
- **Docker Compose alignment** — Synced `docker-compose.runner.yml` with `docker-compose.full.yml`:
  - Added `VISION_WATCH_PROCESSED`, `VISION_WATCH_MODE` env vars
  - Added integrations block (Webhook, MQTT, OPC UA)
  - Added privacy/face anonymization env vars
  - Added `./datasets:/datasets` volume mount
  - Added OPC UA port `4840`
  - Changed `VISION_ALLOW_RUNTIME_SETTINGS` default to `1`
- **README.md rewrite** — Updated to reflect v1.4.x project status:
  - Added features overview section
  - Complete API endpoint documentation (~40+ endpoints)
  - Docker Compose files table with usage examples
  - Privacy and auto-processing examples updated to v1.4.x images
  - Added Dataset/Training, Filters, Registry, Integrations endpoint tables
  - Added OpenVINO env vars, project structure section
  - Updated all Docker image tags and references

## v1.4.0 — 2025-07-15

### Features

#### Privacy & Face Anonymization
- **ULFD face detection engine** — MIT-licensed Ultra-Light-Fast-Detection model via ONNX Runtime
- **Three critical bug fixes** in privacy engine:
  - Prior box decoding now correctly triggers when `priors.shape[0] == boxes.shape[0]`
  - Preprocessing changed from `/255` to `(pixel-127)/128` (ULFD standard)
  - Default `min_score` lowered from `0.5` to `0.15` for ULFD sensitivity
- **Privacy API endpoints:**
  - `GET /api/v1/privacy` — status & configuration
  - `POST /api/v1/privacy` — runtime settings update (mode, min_score, enable/disable)
  - `POST /api/v1/privacy/anonymize` — returns anonymized JPEG
  - `GET /api/v1/demo/image/anonymized?name=` — anonymized demo image
- **Blur and pixelate modes** — configurable via `VISION_PRIVACY_MODE`
- **Smoke test script** — `backend/scripts/privacy_smoke_test.py`

#### Frontend Privacy UI
- **Privacy badge** in inference results: "🔒 X ansikten anonymiserade"
- **Anonymized image preview** — after inference, preview swaps to show anonymized version
- **Settings page controls:**
  - Enable/disable privacy toggle
  - Blur / Pixelate mode selector
  - Min-score slider (0–100%)
  - Model status & ULFD badge
  - Runtime settings warning

#### Internationalization
- Privacy translations for all 7 locales: **sv, en, nl, sk, zh, fr, es**
- 17 new translation keys per locale

#### Integrations
- **OPC UA** server support with runtime start/stop
- **MQTT** publish with configurable broker/topic
- **Webhook** with custom headers
- Test endpoints for webhook and MQTT
- Runtime settings update via `POST /api/v1/integrations`

#### Other
- **Model upload** endpoint (`POST /api/v1/models/upload`)
- **Detection filter system** — create, apply, delete named filters with include/exclude class lists
- **Filtered inference** endpoints (`POST /api/v1/infer/filtered`, `GET /api/v1/demo/infer/filtered`)
- **Watcher status** endpoint

### Fixes
- Fixed all Python lint errors (PEP8 E501 line length, E114 indentation, E303 blank lines, E741 ambiguous variable names)
- Fixed TypeScript `baseUrl` deprecation warning for TS 7.0 (`ignoreDeprecations: "6.0"`)
- Removed mosquitto runtime files from git tracking

### Docker
- Images: `marcussorensson218/vision-runner:1.4.0`, `vision-ui:1.4.0`, `vision-modelprep:1.4.0`, `vision-mcp:1.4.0`
- New environment variables:
  - `VISION_PRIVACY_FACE_BLUR` — enable privacy (1/0)
  - `VISION_PRIVACY_MODEL_PATH` — path to ULFD model
  - `VISION_PRIVACY_MIN_SCORE` — detection threshold (0.0–1.0)
  - `VISION_PRIVACY_MODE` — `blur` or `pixelate`
  - `VISION_PRIVACY_LETTERBOX` — letterbox preprocessing (1/0)
  - `VISION_PRIVACY_NMS_IOU` — NMS IoU threshold
  - `VISION_PRIVACY_BLUR_RADIUS` — Gaussian blur radius
  - `VISION_PRIVACY_PIXELATE_SIZE` — pixelation block size

### Roadmap (plan.md)
- **P11** ✅ Privacy / ansiktsanonymisering — Done
- **P13** 📋 Video Mode (MP4/AVI/MOV)
- **P14** 📋 Valbar Detektionsfunktion (multi-model)
- **P15** 📋 Export av Bearbetade Bilder & Video

---

## v1.3.5

- Documentation updates
- OPC UA 40100 events and state machine
- Integrations API (OPC UA, MQTT, Webhook)
- MCP server for AI assistant integration
- Initial full-stack vision inference application
