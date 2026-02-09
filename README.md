# Industrial Vision System

AI-powered object detection using ONNX Runtime. CPU-first, runs on any platform including Raspberry Pi.

## Features

- **Inference API** — FastAPI backend with ONNX Runtime (YOLOv8, custom models)
- **Video Inference** — Upload MP4/AVI/MOV/MKV/WebM, async processing with SSE progress, annotated export with H.264 preview
- **Watch Folder** — Auto-process images and videos dropped into a directory
- **Web UI** — Next.js frontend with dark mode, bounding box visualization, i18n (7 languages)
- **Privacy / Face Anonymization** — GDPR-ready, ULFD face detector with blur/pixelate modes
- **Detection Filters** — Named filter profiles with include/exclude class lists
- **Model Registry** — Upload, switch, and manage multiple ONNX model bundles
- **Dataset Management** — Create datasets, upload images, annotate, and export for YOLO training
- **Training** — Start/stop YOLO training jobs, view logs and history, export to ONNX/OpenVINO
- **Integrations** — OPC UA (40100-1), MQTT, Webhook — all configurable at runtime, works with both image and video
- **MCP Server** — Model Context Protocol server for AI assistant integration
- **OpenVINO** — Optional Intel hardware acceleration via override compose file

## Quick Start (Docker Hub)

Pull the images:

```bash
docker pull marcussorensson218/vision-runner:1.5.0
docker pull marcussorensson218/vision-modelprep:1.5.0
docker pull marcussorensson218/vision-ui:1.5.0
```

Create a `docker-compose.yml`:

```yaml
services:
  modelprep:
    image: marcussorensson218/vision-modelprep:1.5.0
    environment:
      - VISION_BOOTSTRAP=1
      - VISION_MODEL_PATH=/models/demo/v1/model.onnx
      - VISION_BOOTSTRAP_MODEL=yolov8n.pt
    volumes:
      - ./models:/models

  runner:
    image: marcussorensson218/vision-runner:1.5.0
    restart: unless-stopped
    depends_on:
      modelprep:
        condition: service_completed_successfully
    environment:
      - VISION_MODEL_PATH=/models/demo/v1/model.onnx
      - VISION_WATCH=1
      - VISION_WATCH_INPUT=/input
      - VISION_WATCH_OUTPUT=/output
      - VISION_PRIVACY_FACE_BLUR=0
      - VISION_PRIVACY_MODEL_PATH=/models/privacy/ulfd/v1/model.onnx
    volumes:
      - ./models:/models:ro
      - ./datasets:/datasets
      - ./input:/input
      - ./output:/output
    ports:
      - "8000:8000"
      - "4840:4840"

  ui:
    image: marcussorensson218/vision-ui:1.5.0
    restart: unless-stopped
    depends_on:
      - runner
    environment:
      - NEXT_PUBLIC_API_BASE=http://localhost:8000
    ports:
      - "3000:3000"

  mcp:
    image: marcussorensson218/vision-mcp:1.5.0
    depends_on:
      - runner
    environment:
      - VISION_API_URL=http://runner:8000
      - MCP_TRANSPORT=sse
    ports:
      - "8080:8080"

  mqtt:
    image: eclipse-mosquitto:2.0
    restart: unless-stopped
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - ./mosquitto/data:/mosquitto/data
      - ./mosquitto/log:/mosquitto/log
```

Start everything:

```bash
docker compose up -d
```

Open:

- **UI**: <http://localhost:3000>
- **API docs**: <http://localhost:8000/docs>
- **MCP (SSE)**: <http://localhost:8080/sse>

## Docker Compose Files

| File | Purpose |
|------|---------|
| `docker-compose.full.yml` | Full stack: runner + UI + MCP + MQTT |
| `docker-compose.runner.yml` | Runner only (headless, no UI/MCP/MQTT) |
| `docker-compose.builder.yml` | One-shot model bootstrap/export |
| `docker-compose.openvino.yml` | Override: OpenVINO EP on Intel hardware |

```bash
# Full stack
docker compose -f docker-compose.full.yml up --build

# Runner only
docker compose -f docker-compose.runner.yml up --build

# Runner with OpenVINO
docker compose -f docker-compose.runner.yml -f docker-compose.openvino.yml up --build
```

## Volume Mappings

| Container Path | Description | Example |
|----------------|-------------|---------|
| `/models` | ONNX model bundles | `-v ./models:/models:ro` |
| `/input` | Images to process | `-v ./input:/input` |
| `/output` | Detection results (JSON) | `-v ./output:/output` |
| `/datasets` | Training datasets | `-v ./datasets:/datasets` |

## Environment Variables

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_MODEL_PATH` | — | **Required.** Path to ONNX model |

### Watch Folder (Auto-Processing)

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_WATCH` | `1` | Enable folder watching |
| `VISION_WATCH_INPUT` | `/input` | Folder to watch |
| `VISION_WATCH_OUTPUT` | `/output` | JSON results folder |
| `VISION_WATCH_PROCESSED` | — | Move processed images here |
| `VISION_WATCH_MODE` | `json` | `json`, `move`, or `both` |

### Video Inference

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_VIDEO_FRAME_INTERVAL` | `5` | Sample every Nth frame |
| `VISION_VIDEO_MAX_FRAMES` | `300` | Max frames to process per video |

### Upload & Security

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_SAVE_UPLOADS` | `0` | Persist uploaded images |
| `VISION_DEMO_ALLOW_MUTATIONS` | `0` | Allow file deletion via API |
| `VISION_ALLOW_RUNTIME_SETTINGS` | `1` | Allow settings changes from UI |

### Integrations

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_WEBHOOK_URL` | — | HTTP POST endpoint for results |
| `VISION_MQTT_BROKER` | — | MQTT broker hostname |
| `VISION_MQTT_TOPIC` | `vision/results` | MQTT topic for results |
| `VISION_OPCUA_ENABLE` | `0` | Enable OPC UA server on port 4840 |

### Privacy & Anonymization

Optional face anonymization before inference (GDPR compliance).
Uses the **Ultra-Light-Fast-Generic-Face-Detector** (ULFD, MIT license) — a ~1 MB ONNX model suitable for CPU and commercial use.

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_PRIVACY_FACE_BLUR` | `0` | Enable privacy pre-processing |
| `VISION_PRIVACY_MODEL_PATH` | — | Path to face detector ONNX model |
| `VISION_PRIVACY_MODE` | `blur` | `blur` or `pixelate` |
| `VISION_PRIVACY_MIN_SCORE` | `0.15` | Minimum face score to anonymize |
| `VISION_PRIVACY_BLUR_RADIUS` | `12` | Gaussian blur radius |
| `VISION_PRIVACY_PIXELATE_SIZE` | `10` | Pixelation block size |
| `VISION_PRIVACY_LETTERBOX` | `1` | Use letterbox preprocessing |
| `VISION_PRIVACY_NMS_IOU` | `0.3` | NMS IoU threshold |

### OpenVINO (Intel)

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_ORT_PROVIDERS` | `CPUExecutionProvider` | ONNX Runtime execution providers |
| `VISION_OPENVINO_DEVICE_TYPE` | `CPU` | OpenVINO device type |

## API Endpoints

### Inference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/infer` | POST | Run inference on uploaded image |
| `/api/v1/infer/filtered` | POST | Infer with a named detection filter |
| `/api/v1/infer/video` | POST | Upload video and start async inference |
| `/api/v1/infer/video/status/{job_id}` | GET | SSE progress stream for video job |
| `/api/v1/infer/video/result/{job_id}` | GET | Full per-frame detection results |
| `/api/v1/infer/video/export/{job_id}` | POST | Render annotated video (boxes/labels/privacy) |
| `/api/v1/infer/video/export/{job_id}` | GET | Download rendered video |
| `/api/v1/infer/video/preview/{job_id}` | GET | Stream rendered video for playback |
| `/api/v1/demo/files` | GET | List files in input folder |
| `/api/v1/demo/infer?name=` | GET | Infer on existing file |
| `/api/v1/demo/infer/filtered?name=` | GET | Filtered infer on existing file |
| `/api/v1/demo/image?name=` | GET | Serve an input image |
| `/api/v1/demo/image/anonymized?name=` | GET | Serve anonymized version |
| `/api/v1/demo/clear` | POST | Clear input folder (guarded) |

### Privacy

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/privacy` | GET | Privacy status and configuration |
| `/api/v1/privacy` | POST | Update privacy settings at runtime |
| `/api/v1/privacy/anonymize` | POST | Anonymize an uploaded image |

### Models & Registry

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/models` | GET | Current active model info |
| `/api/v1/models/labels` | GET | Class labels for active model |
| `/api/v1/models/reload` | POST | Reload the active model |
| `/api/v1/models/upload` | POST | Upload a new model bundle |
| `/api/v1/models/bundle` | GET | Download active model as bundle |
| `/api/v1/models/bundle/import` | POST | Import a model bundle ZIP |
| `/api/v1/registry` | GET | List all available model bundles |
| `/api/v1/registry/activate` | POST | Activate a model bundle |

### Detection Filters

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/filters` | GET | List all filters |
| `/api/v1/filters/{name}` | GET | Get a filter |
| `/api/v1/filters` | POST | Create a filter |
| `/api/v1/filters/{name}` | DELETE | Delete a filter |

### Datasets & Training

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/datasets` | GET / POST | List or create datasets |
| `/api/v1/datasets/{name}` | GET / DELETE | Get or delete a dataset |
| `/api/v1/datasets/{name}/images` | GET / POST | List or upload images |
| `/api/v1/datasets/{name}/images/{id}/annotations` | GET / PUT | Read or update annotations |
| `/api/v1/datasets/{name}/classes` | GET / PUT | Manage class labels |
| `/api/v1/datasets/{name}/export` | POST | Export dataset (YOLO format) |
| `/api/v1/training/start` | POST | Start a training job |
| `/api/v1/training/status` | GET | Training job status |
| `/api/v1/training/stop` | POST | Stop the running job |
| `/api/v1/training/logs` | GET | Training logs |
| `/api/v1/training/history` | GET | Previous training runs |
| `/api/v1/training/export` | POST | Export trained model to ONNX |
| `/api/v1/training/export/openvino` | POST | Export to OpenVINO IR |

### Integrations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/integrations` | GET | Integration status (OPC UA, MQTT, Webhook) |
| `/api/v1/integrations` | POST | Update integration settings |
| `/api/v1/integrations/test/webhook` | POST | Send a test webhook |
| `/api/v1/integrations/test/mqtt` | POST | Send a test MQTT message |

### System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/health/ready` | GET | Readiness check |
| `/api/v1/settings` | GET / POST | View or update runtime settings |
| `/api/v1/watcher/status` | GET | Watch folder status |

### Inference via cURL

```bash
curl -X POST http://localhost:8000/api/v1/infer -F "image=@photo.jpg"
```

## Auto-Processing Example

Process images automatically and move them to a "processed" folder:

```yaml
services:
  runner:
    image: marcussorensson218/vision-runner:1.5.0
    environment:
      - VISION_MODEL_PATH=/models/demo/v1/model.onnx
      - VISION_WATCH=1
      - VISION_WATCH_PROCESSED=/input/processed
      - VISION_WATCH_MODE=both
    volumes:
      - ./models:/models:ro
      - ./inbox:/input
      - ./results:/output
    ports:
      - "8000:8000"
```

**Flow:**

1. Drop image into `./inbox/`
2. Detection runs automatically
3. JSON results saved to `./results/`
4. Image moved to `./inbox/processed/`

## Privacy Example

Enable face anonymization (GDPR):

```yaml
services:
  runner:
    image: marcussorensson218/vision-runner:1.5.0
    environment:
      - VISION_MODEL_PATH=/models/demo/v1/model.onnx
      - VISION_PRIVACY_FACE_BLUR=1
      - VISION_PRIVACY_MODEL_PATH=/models/privacy/ulfd/v1/model.onnx
      - VISION_PRIVACY_MIN_SCORE=0.15
    volumes:
      - ./models:/models:ro
      - ./input:/input
      - ./output:/output
    ports:
      - "8000:8000"
```

When enabled, faces are automatically anonymized before the main detection model runs. The API response includes `privacy_applied` (boolean) and `privacy_faces` (count) fields.

## Model Bundle Format

```
models/
└── demo/
    └── v1/
        ├── model.onnx     # ONNX model with NMS
        ├── labels.txt     # Class labels (one per line)
        └── meta.json      # Optional metadata
```

## Industrial Connectivity

The system is designed for Industry 4.0 integration:

- **OPC UA Server (Port 4840)**:
  - Standard: OPC 40100-1 Machine Vision Companion Specification
  - Features: State Machine, Result Events, Remote Control (Start/Stop/Model Select)
  - Legacy Mode: Simplified nodes for older PLCs
- **MQTT (Port 1883)**:
  - Built-in Mosquitto broker (in full compose)
  - Publishes JSON results to configurable topic
- **Webhook**:
  - HTTP POST with custom headers
  - Test endpoint for verification

See [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) for full integration documentation.

## MCP Server (AI Assistant Integration)

The MCP server allows AI assistants (e.g. Open-WebUI, Claude) to use Vision for image analysis.

| Tool | Description |
|------|-------------|
| `analyze_image` | Analyze image from URL |
| `analyze_image_base64` | Analyze base64-encoded image |
| `analyze_with_filter` | Analyze with detection filter |
| `list_filters` / `create_filter` / `delete_filter` | Manage detection filters |
| `list_models` / `activate_model` | Model management |
| `get_system_status` | System health check |

Configure Open-WebUI to connect to `http://localhost:8080/sse`.

## Platform Support

| Platform | Architecture | Status |
|----------|--------------|--------|
| Windows | amd64 | ✅ Tested |
| Linux | amd64 | ✅ Tested |
| macOS | amd64/arm64 | ✅ Tested |
| Raspberry Pi | arm64 | ✅ Tested |

## Docker Images

| Image | Description |
|-------|-------------|
| `marcussorensson218/vision-runner` | Inference API server |
| `marcussorensson218/vision-modelprep` | Model bootstrap/preparation |
| `marcussorensson218/vision-ui` | Web UI (Next.js) |
| `marcussorensson218/vision-mcp` | MCP server for AI assistants |
| `eclipse-mosquitto:2.0` | MQTT broker (official image) |

### Tags

| Tag | Description |
|-----|-------------|
| `latest` | Most recent stable build |
| `1.5.0` | Current version (video mode) |
| `1.4.3` | Previous stable (docker compose alignment) |
| `1.3.5` | Industrial integrations |

## Project Structure

```
backend/         FastAPI + ONNX Runtime inference engine
frontend/        Next.js web UI
mcp-server/      MCP server for AI assistants
models/          ONNX model bundles + privacy model
datasets/        Training datasets
input/           Watch folder input
output/          Detection results
scripts/         Helper scripts
docs/            Extended documentation
mosquitto/       MQTT broker config
```

## Support

Issues and feature requests: [GitHub Repository](https://github.com/msorenss/vision)
