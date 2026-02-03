# Volvo Cars Vision

AI-powered object detection using ONNX Runtime. CPU-first, runs on any platform including Raspberry Pi.

## Quick Start (Docker Hub)

Pull the images:

```bash
docker pull marcussorensson218/vision-runner:1.2.0
docker pull marcussorensson218/vision-modelprep:1.2.0
docker pull marcussorensson218/vision-ui:1.2.0
```

Create a `docker-compose.yml`:

```yaml
version: "3.8"
services:
  modelprep:
    image: marcussorensson218/vision-modelprep:1.2.0
    environment:
      - VISION_BOOTSTRAP=1
      - VISION_MODEL_PATH=/models/demo/v1/model.onnx
      - VISION_BOOTSTRAP_MODEL=yolov8n.pt
    volumes:
      - ./models:/models

  runner:
    image: marcussorensson218/vision-runner:1.2.0
    restart: unless-stopped
    depends_on:
      modelprep:
        condition: service_completed_successfully
    environment:
      - VISION_MODEL_PATH=/models/demo/v1/model.onnx
      - VISION_WATCH=1
    volumes:
      - ./models:/models:ro
      - ./input:/input
      - ./output:/output
    ports:
      - "8000:8000"
      - "4840:4840"

  ui:
    image: marcussorensson218/vision-ui:1.2.0
    restart: unless-stopped
    depends_on:
      - runner
    environment:
      - NEXT_PUBLIC_API_BASE=http://localhost:8000
    ports:
      - "3000:3000"
```

Start everything:

```bash
docker compose up -d
```

Open:

- **UI**: <http://localhost:3000>
- **API**: <http://localhost:8000/docs>

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

### Integrations

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_WEBHOOK_URL` | - | HTTP POST endpoint for results |
| `VISION_MQTT_BROKER` | - | MQTT broker hostname |
| `VISION_MQTT_TOPIC` | `vision/results` | MQTT topic for results |
| `VISION_OPCUA_ENABLE` | `0` | Enable OPC UA server on port 4840 |

## Auto-Processing Example

Process images automatically and move them to a "processed" folder:

```yaml
services:
  runner:
    image: marcussorensson218/vision-runner:1.2.0
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
| `/api/v1/demo/infer?name=file.jpg` | GET | Infer on existing file |

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

## Docker Images

| Image | Description |
|-------|-------------|
| `marcussorensson218/vision-runner` | Inference API server |
| `marcussorensson218/vision-modelprep` | Model bootstrap/preparation |
| `marcussorensson218/vision-ui` | Web UI (Next.js) |

### Tags

| Tag | Description |
|-----|-------------|
| `latest` | Most recent stable build |
| `1.2.0` | Current version (recommended) |

## MCP Server (AI Assistant Integration)

The MCP (Model Context Protocol) server allows AI assistants to use Vision for image analysis.

### Available Tools

| Tool | Description |
|------|-------------|
| `analyze_image` | Analyze image from URL |
| `analyze_image_base64` | Analyze base64-encoded image |
| `analyze_with_filter` | Analyze with detection filter |
| `list_filters` / `create_filter` | Manage detection filters |
| `list_models` / `activate_model` | Model management |
| `get_system_status` | System health check |

### Usage with Open-WebUI

Add the MCP service to your docker-compose:

```yaml
  mcp:
    build:
      context: ./mcp-server
    depends_on:
      - runner
    environment:
      - VISION_API_URL=http://runner:8000
    ports:
      - "8080:8080"
```

Configure Open-WebUI to connect to `http://vision-mcp:8080/sse`

Example prompts:

- "Analyze this image: <https://example.com/photo.jpg>"
- "Create a filter that only detects vehicles"
- "What's the system status?"

## Support

Issues and feature requests: [GitHub Repository](https://github.com/marcussorensson218/vision)
