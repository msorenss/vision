# Industrial Vision System

AI-powered object detection using ONNX Runtime. CPU-first, runs on any platform including Raspberry Pi.

## Quick Start (Docker Hub)

```bash
docker pull marcussorensson218/vision-runner:1.5.5
docker pull marcussorensson218/vision-modelprep:1.5.5
docker pull marcussorensson218/vision-ui:1.5.5
```

Minimal single-container setup (API only):

```bash
docker run -d \
  --name vision-runner \
  -v ./models:/models:ro \
  -v ./input:/input \
  -v ./output:/output \
  -e VISION_MODEL_PATH=/models/demo/v1/model.onnx \
  -p 8000:8000 \
  marcussorensson218/vision-runner:1.5.5
```

## Volume Mappings

| Container Path | Description | Example |
|----------------|-------------|---------|
| `/models` | ONNX model bundles (read-only) | `-v ./models:/models:ro` |
| `/input` | Images to process | `-v ./input:/input` |
| `/output` | Detection results (JSON) | `-v ./output:/output` |

## Environment Variables

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_MODEL_PATH` | - | **Required.** Path to ONNX model |

### Watch Folder (Auto-Processing)

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_WATCH` | `1` | Enable folder watching |
| `VISION_WATCH_INPUT` | `/input` | Folder to watch |
| `VISION_WATCH_OUTPUT` | `/output` | JSON results folder |
| `VISION_WATCH_PROCESSED` | - | Move processed images here |
| `VISION_WATCH_MODE` | `json` | `json`, `move`, `both`, or `annotated` |

### Export (New in v1.5.5)

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_EXPORT_ANNOTATED` | `0` | Save annotated images from watch folder |
| `VISION_EXPORT_FORMAT` | `jpg` | Annotated output format (`jpg` or `png`) |

### Upload & Security

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_SAVE_UPLOADS` | `0` | Persist uploaded images |
| `VISION_DEMO_ALLOW_MUTATIONS` | `0` | Allow file deletion via API |
| `VISION_ALLOW_RUNTIME_SETTINGS` | `1` | Allow settings changes from UI |

### Integrations

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_WEBHOOK_URL` | — | Push JSON results via HTTP POST |
| `VISION_MQTT_BROKER` | — | Enable MQTT publishing |
| `VISION_MQTT_TOPIC` | `vision/results` | MQTT Topic |
| `VISION_OPCUA_ENABLE` | `0` | Enable OPC UA Server (Port 4840) |

### Privacy & Anonymization

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_PRIVACY_FACE_BLUR` | `0` | Enable face anonymization |
| `VISION_PRIVACY_MODEL_PATH` | — | Path to ULFD face detector model |
| `VISION_PRIVACY_MODE` | `blur` | `blur` or `pixelate` |
| `VISION_PRIVACY_MIN_SCORE` | `0.15` | Minimum face score to anonymize |

### Video Inference

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_VIDEO_FRAME_INTERVAL` | `5` | Sample every Nth frame |
| `VISION_VIDEO_MAX_FRAMES` | `300` | Max frames to process per video |

## Auto-Processing Example

Process images automatically and move them to a "processed" folder:

```bash
docker run -d \
  --name vision-runner \
  -v ./models:/models:ro \
  -v ./inbox:/input \
  -v ./results:/output \
  -e VISION_MODEL_PATH=/models/demo/v1/model.onnx \
  -e VISION_WATCH=1 \
  -e VISION_WATCH_PROCESSED=/input/processed \
  -e VISION_WATCH_MODE=both \
  -p 8000:8000 \
  marcussorensson218/vision-runner:1.5.5
```

**Flow:**

1. Drop image into `./inbox/`
2. Detection runs automatically
3. JSON results saved to `./results/`
4. Image moved to `./inbox/processed/`

## Docker Compose (Full Stack)

```yaml
services:
  modelprep:
    image: marcussorensson218/vision-modelprep:1.5.5
    environment:
      - VISION_BOOTSTRAP=1
      - VISION_MODEL_PATH=/models/demo/v1/model.onnx
      - VISION_BOOTSTRAP_MODEL=yolov8n.pt
    volumes:
      - ./models:/models

  runner:
    image: marcussorensson218/vision-runner:1.5.5
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
      - VISION_EXPORT_ANNOTATED=0
      - VISION_EXPORT_FORMAT=jpg
    volumes:
      - ./models:/models:ro
      - ./input:/input
      - ./output:/output
      - ./datasets:/datasets
    ports:
      - "8000:8000"
      - "4840:4840"

  ui:
    image: marcussorensson218/vision-ui:1.5.5
    restart: unless-stopped
    depends_on:
      - runner
    environment:
      - NEXT_PUBLIC_API_BASE=http://localhost:8000
    ports:
      - "3000:3000"

  mcp:
    image: marcussorensson218/vision-mcp:1.5.5
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
```

```bash
docker compose up -d
```

Open:
- **UI**: http://localhost:3000
- **API docs**: http://localhost:8000/docs
- **MCP**: http://localhost:8080/sse

## Model Bundle Format

```
models/
└── demo/
    └── v1/
        ├── model.onnx     # ONNX model with NMS
        ├── labels.txt     # Class labels (one per line)
        └── meta.json      # Optional metadata
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/infer` | POST | Run inference on image |
| `/api/v1/infer/filtered` | POST | Infer with active filter |
| `/api/v1/infer/video` | POST | Upload video for async inference |
| `/api/v1/demo/files` | GET | List files in input |
| `/api/v1/demo/infer` | GET | Infer on existing file |
| `/api/v1/demo/infer/filtered` | GET | Filtered infer on existing file |
| `/api/v1/tasks` | GET | List available detection tasks |
| `/api/v1/filters` | GET | List detection filters |
| `/api/v1/export/image` | GET/POST | Export annotated image |
| `/api/v1/export/batch` | POST | Batch export images as ZIP |
| `/api/v1/privacy` | GET | Privacy status |
| `/api/v1/models/upload` | POST | Upload new model bundle |
| `/api/v1/integrations` | GET | Integration status |

### Inference via cURL

```bash
curl -X POST http://localhost:8000/api/v1/infer -F "image=@photo.jpg"
```

## Platform Support

| Platform | Architecture | Status |
|----------|--------------|--------|
| Windows | amd64 | ✅ Tested |
| Linux | amd64 | ✅ Tested |
| macOS | amd64/arm64 | ✅ Tested |
| Raspberry Pi | arm64 | ✅ Tested |

## Tags

| Tag | Description |
|-----|-------------|
| `latest` | Most recent stable build |
| `1.5.5` | Current version (export + task picker + filters) |
| `1.5.0` | Video mode |
| `1.4.3` | Docker compose alignment |
| `1.3.5` | Industrial integrations |

## Support

Issues and feature requests: [GitHub Repository](https://github.com/msorenss/vision)
