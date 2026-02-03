# Vision Integration Guide

This document describes how to configure and use external integrations for publishing Vision detection results to OPC UA, MQTT, and Webhooks.

## Overview

Vision supports three integration methods for publishing inference results to external systems:

| Integration | Protocol | Use Case |
|------------|----------|----------|
| **OPC UA** | Industrial automation standard | PLCs, SCADA systems, factory automation |
| **MQTT** | Lightweight messaging protocol | IoT systems, message brokers, event-driven architectures |
| **Webhook** | HTTP POST requests | REST APIs, serverless functions, custom backends |

## Configuration

All integrations can be configured via:

1. **Environment variables** (at container startup)
2. **Settings UI** (runtime, if `VISION_ALLOW_RUNTIME_SETTINGS=1`)
3. **REST API** (`POST /api/v1/integrations`)
4. **MCP Tools** (`configure_opcua`, `configure_mqtt`, `configure_webhook`)

---

## OPC UA Server

The Vision OPC UA server exposes detection results as OPC UA nodes that can be subscribed to by any OPC UA client.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_OPCUA_ENABLE` | `0` | Set to `1` to enable the OPC UA server |
| `VISION_OPCUA_PORT` | `4840` | OPC UA server port |
| `VISION_OPCUA_ENDPOINT` | Auto-generated | Full endpoint URL (usually auto-generated from port) |
| `VISION_OPCUA_UPDATE_INTERVAL_MS` | `0` | Minimum interval between node updates (0 = immediate) |

### Namespace

The OPC UA server uses the namespace:

```
http://volvocars.com/vision
```

### Node Structure

```
VisionSystem (Object)
├── ActiveModel (String)
│   └── Current model path (e.g., "/models/v1/model.rknn")
│
├── State (Int32)
│   └── Current system state:
│       0 = Off
│       1 = Ready
│       2 = Processing
│       3 = Error
│
└── Results (Object)
    ├── LastResult (String)
    │   └── JSON string of the last detection result
    │
    └── DisplayCount (UInt32)
        └── Number of objects detected in the last frame
```

### Example OPC UA Clients

**Python (asyncua):**

```python
from asyncua import Client

async with Client("opc.tcp://vision-host:4840/freeopcua/server/") as client:
    ns_idx = await client.get_namespace_index("http://volvocars.com/vision")
    
    # Read current state
    state_node = client.get_node(f"ns={ns_idx};i=2")  # VisionSystem.State
    state = await state_node.get_value()
    print(f"State: {state}")
    
    # Subscribe to results
    results_node = client.get_node(f"ns={ns_idx};i=4")  # VisionSystem.Results.LastResult
    # ... create subscription handler
```

**Node.js (node-opcua):**

```javascript
const { OPCUAClient } = require("node-opcua");

const client = OPCUAClient.create({ endpointMustExist: false });
await client.connect("opc.tcp://vision-host:4840/freeopcua/server/");
const session = await client.createSession();

const value = await session.read({
  nodeId: "ns=1;s=VisionSystem.State"
});
```

---

## MQTT Client

Vision can publish detection results to an MQTT broker for integration with IoT systems and message-driven architectures.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_MQTT_BROKER` | *none* | MQTT broker hostname (required to enable MQTT) |
| `VISION_MQTT_PORT` | `1883` | MQTT broker port |
| `VISION_MQTT_TOPIC` | `vision/results` | Topic to publish results to |
| `VISION_MQTT_USERNAME` | *none* | Username for broker authentication |
| `VISION_MQTT_PASSWORD` | *none* | Password for broker authentication |

### Topic Structure

Results are published to the configured topic (default: `vision/results`).

For multi-camera setups, you can customize the topic per deployment:

- `factory/line1/vision/results`
- `warehouse/dock3/vision/results`

### Message Payload

```json
{
  "image": "frame_001.jpg",
  "timestamp": "2024-01-15T10:30:00.123Z",
  "model": "/models/defect_detection/model.rknn",
  "inference_time_ms": 45.2,
  "detections": [
    {
      "class_id": 0,
      "label": "defect",
      "score": 0.95,
      "box": {
        "x1": 100,
        "y1": 150,
        "x2": 200,
        "y2": 250
      }
    },
    {
      "class_id": 1,
      "label": "scratch",
      "score": 0.82,
      "box": {
        "x1": 300,
        "y1": 400,
        "x2": 350,
        "y2": 450
      }
    }
  ],
  "detection_count": 2
}
```

### Example MQTT Subscribers

**Python (paho-mqtt):**

```python
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, msg):
    result = json.loads(msg.payload)
    print(f"Detected {result['detection_count']} objects")
    for det in result['detections']:
        print(f"  - {det['label']}: {det['score']:.2f}")

client = mqtt.Client()
client.on_message = on_message
client.connect("mqtt-broker", 1883)
client.subscribe("vision/results")
client.loop_forever()
```

**Node.js (mqtt):**

```javascript
const mqtt = require('mqtt');

const client = mqtt.connect('mqtt://mqtt-broker:1883');

client.on('connect', () => {
  client.subscribe('vision/results');
});

client.on('message', (topic, message) => {
  const result = JSON.parse(message.toString());
  console.log(`Detected ${result.detection_count} objects`);
});
```

---

## Webhook

Vision can send HTTP POST requests to a configured webhook URL for each detection result.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_WEBHOOK_URL` | *none* | Target URL to POST results to |
| `VISION_WEBHOOK_HEADERS` | `{}` | JSON string of custom HTTP headers |

### Request Format

- **Method:** `POST`
- **Content-Type:** `application/json`
- **Body:** Same JSON payload as MQTT (see above)

### Custom Headers

For authentication or custom routing, set headers as a JSON string:

```bash
VISION_WEBHOOK_HEADERS='{"Authorization": "Bearer YOUR_API_TOKEN", "X-Source": "vision-system"}'
```

### Webhook Payload

```json
{
  "image": "frame_001.jpg",
  "timestamp": "2024-01-15T10:30:00.123Z",
  "model": "/models/defect_detection/model.rknn",
  "inference_time_ms": 45.2,
  "detections": [
    {
      "class_id": 0,
      "label": "defect",
      "score": 0.95,
      "box": {
        "x1": 100,
        "y1": 150,
        "x2": 200,
        "y2": 250
      }
    }
  ],
  "detection_count": 1
}
```

### Example Webhook Receivers

**Express.js:**

```javascript
const express = require('express');
const app = express();
app.use(express.json());

app.post('/vision-webhook', (req, res) => {
  const result = req.body;
  console.log(`Received detection from ${result.image}`);
  
  // Process detections
  for (const det of result.detections) {
    if (det.label === 'defect' && det.score > 0.9) {
      // Trigger alert
      console.log('HIGH CONFIDENCE DEFECT DETECTED!');
    }
  }
  
  res.status(200).json({ received: true });
});

app.listen(3001);
```

**Python Flask:**

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/vision-webhook', methods=['POST'])
def handle_vision():
    result = request.json
    print(f"Received {result['detection_count']} detections")
    
    # Filter high-confidence detections
    critical = [d for d in result['detections'] if d['score'] > 0.9]
    if critical:
        # Send alert
        pass
    
    return jsonify({"ok": True})

if __name__ == '__main__':
    app.run(port=3001)
```

---

## API Reference

### GET /api/v1/integrations

Returns current status of all integrations.

**Response:**

```json
{
  "opcua": {
    "available": true,
    "enabled": true,
    "running": true,
    "endpoint": "opc.tcp://0.0.0.0:4840/freeopcua/server/",
    "port": 4840,
    "namespace": "http://volvocars.com/vision",
    "update_interval_ms": 0
  },
  "mqtt": {
    "available": true,
    "configured": true,
    "broker": "mqtt.example.com",
    "port": 1883,
    "topic": "vision/results",
    "username": null
  },
  "webhook": {
    "configured": true,
    "url": "https://api.example.com/vision",
    "has_custom_headers": false
  }
}
```

### POST /api/v1/integrations

Update integration settings at runtime.

> **Note:** Requires `VISION_ALLOW_RUNTIME_SETTINGS=1`

**Request Body:**

```json
{
  "opcua_enabled": true,
  "opcua_port": 4840,
  "opcua_update_interval_ms": 100,
  "mqtt_broker": "mqtt.example.com",
  "mqtt_port": 1883,
  "mqtt_topic": "factory/vision/results",
  "mqtt_username": "vision",
  "mqtt_password": "secret",
  "webhook_url": "https://api.example.com/webhook",
  "webhook_headers": "{\"Authorization\": \"Bearer token\"}"
}
```

All fields are optional. Only provided fields are updated.

### POST /api/v1/integrations/test/webhook

Send a test message to the configured webhook.

### POST /api/v1/integrations/test/mqtt

Publish a test message to the configured MQTT broker.

---

## MCP Tools

The Vision MCP server provides tools for managing integrations:

| Tool | Description |
|------|-------------|
| `get_integrations_status` | Get current status of all integrations |
| `configure_opcua` | Configure OPC UA server settings |
| `configure_mqtt` | Configure MQTT client settings |
| `configure_webhook` | Configure webhook settings |
| `test_webhook` | Send a test message to the webhook |
| `test_mqtt` | Publish a test message to MQTT |

### Example Usage

```
> Use the configure_mqtt tool to set broker to "mqtt.local" and topic to "factory/line1/vision"

> Then use test_mqtt to verify the connection works
```

---

## Docker Compose Configuration

Example `docker-compose.yml` with all integrations enabled:

```yaml
services:
  vision:
    image: vision-runner:latest
    environment:
      # OPC UA
      - VISION_OPCUA_ENABLE=1
      - VISION_OPCUA_PORT=4840
      
      # MQTT
      - VISION_MQTT_BROKER=mqtt-broker
      - VISION_MQTT_PORT=1883
      - VISION_MQTT_TOPIC=vision/results
      
      # Webhook
      - VISION_WEBHOOK_URL=http://backend:3001/vision-webhook
      
      # Allow runtime changes
      - VISION_ALLOW_RUNTIME_SETTINGS=1
    ports:
      - "8000:8000"
      - "4840:4840"  # OPC UA

  mqtt-broker:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"
```

---

## Troubleshooting

### OPC UA server not starting

1. Check if `asyncua` is installed: `pip show asyncua`
2. Verify `VISION_OPCUA_ENABLE=1` is set
3. Check logs for port conflicts

### MQTT messages not publishing

1. Verify broker is reachable: `nc -zv mqtt-broker 1883`
2. Check if `aiomqtt` is installed: `pip show aiomqtt`
3. Test with `test_mqtt` API endpoint

### Webhook requests failing

1. Verify URL is correct and accessible
2. Check for SSL/TLS issues with HTTPS
3. Verify custom headers are valid JSON
4. Test with `test_webhook` API endpoint
