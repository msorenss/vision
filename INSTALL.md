# Volvo Cars Vision

AI-powered object detection using ONNX Runtime. CPU-first, runs on any platform including Raspberry Pi.

## Quick Start

```bash
docker pull marcussorensson218/volvo-vision:latest

docker run -d \
  --name volvo-vision \
  -v /path/to/models:/models:ro \
  -v /path/to/input:/input \
  -v /path/to/output:/output \
  -e VISION_MODEL_PATH=/models/demo/v1/model.onnx \
  -p 8000:8000 \
  marcussorensson218/volvo-vision:latest
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
| `VISION_WATCH_MODE` | `json` | `json`, `move`, or `both` |

### Upload & Security

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_SAVE_UPLOADS` | `0` | Persist uploaded images |
| `VISION_DEMO_ALLOW_MUTATIONS` | `0` | Allow file deletion via API |
| `VISION_ALLOW_RUNTIME_SETTINGS` | `0` | Allow settings changes from UI |

### Integration (New in v1.1.0)

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_WEBHOOK_URL` | - | Push JSON results via HTTP POST |
| `VISION_MQTT_BROKER` | - | Enable MQTT publishing |
| `VISION_MQTT_TOPIC` | `vision/results` | MQTT Topic |
| `VISION_OPCUA_ENABLE` | `0` | Enable OPC UA Server (Port 4840) |

## Auto-Processing Example

Process images automatically and move them to a "processed" folder:

```bash
docker run -d \
  --name volvo-vision \
  -v ./models:/models:ro \
  -v ./inbox:/input \
  -v ./results:/output \
  -e VISION_MODEL_PATH=/models/demo/v1/model.onnx \
  -e VISION_WATCH=1 \
  -e VISION_WATCH_PROCESSED=/input/processed \
  -e VISION_WATCH_MODE=both \
  -p 8000:8000 \
  marcussorensson218/volvo-vision:latest
```

**Flow:**
1. Drop image into `./inbox/`
2. Detection runs automatically
3. JSON results saved to `./results/`
4. Image moved to `./inbox/processed/`

## Docker Compose

```yaml
version: "3.8"
services:
  vision:
    image: marcussorensson218/volvo-vision:latest
    restart: unless-stopped
    environment:
      - VISION_MODEL_PATH=/models/demo/v1/model.onnx
      - VISION_WATCH=1
      - VISION_WATCH_PROCESSED=/input/processed
      - VISION_WATCH_MODE=both
    volumes:
      - ./models:/models:ro
      - ./input:/input
      - ./output:/output
    ports:
      - "8000:8000"
```

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
| `/api/v1/demo/files` | GET | List files in input |
| `/api/v1/demo/infer` | GET | Infer on existing file |
| `/api/v1/infer/filtered` | POST | Infer with active filter |
| `/api/v1/demo/infer/filtered` | GET | Infer on active file with filter |
| `/api/v1/models/upload` | POST | Upload new model bundle |

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
| `v1.0.0` | Pinned version (recommended) |

## Support

Issues and feature requests: [GitHub Repository](https://github.com/marcussorensson218/volvo-vision)
