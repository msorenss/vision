# Vision MCP Server

MCP (Model Context Protocol) server that exposes Vision AI object detection to LLM assistants.

## Available Tools

| Tool | Description |
|------|-------------|
| `analyze_image` | Analyze image from URL |
| `analyze_image_base64` | Analyze base64-encoded image |
| `analyze_with_filter` | Analyze with detection filter |
| `list_filters` | List available filters |
| `create_filter` | Create new filter |
| `delete_filter` | Delete a filter |
| `list_models` | List available models |
| `activate_model` | Switch active model |
| `get_system_status` | Get system health |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_API_URL` | `http://runner:8000` | Vision Runner API URL |
| `MCP_TRANSPORT` | `sse` | Transport: `sse` or `stdio` |

## Usage with Open-WebUI

1. Start the Vision stack with MCP server
2. Configure Open-WebUI to use the MCP endpoint
3. Your LLM can now analyze images!

Example prompts:

- "Analyze this image: <https://example.com/image.jpg>"
- "Create a filter that only detects vehicles"
- "What objects are in this photo?"
