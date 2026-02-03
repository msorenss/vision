"""
Vision MCP Server - Exposes Vision AI capabilities to LLM assistants

This server uses the Model Context Protocol (MCP) to allow AI assistants
in Open-WebUI and other MCP-compatible clients to analyze images using
the Vision object detection system.
"""
import os
import logging
from fastmcp import FastMCP

from .client import VisionClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vision-mcp")

# Initialize MCP server
mcp = FastMCP("vision")

# Initialize Vision API client
vision_client: VisionClient | None = None


def get_client() -> VisionClient:
    """Get or create Vision API client."""
    global vision_client
    if vision_client is None:
        vision_client = VisionClient()
    return vision_client


# ============================================================================
# Tools
# ============================================================================

@mcp.tool()
def analyze_image(image_url: str) -> dict:
    """
    Analyze an image and detect objects using YOLO object detection.
    
    Args:
        image_url: URL to the image to analyze
        
    Returns:
        Detection results with bounding boxes, class labels, and confidence scores
    """
    logger.info(f"Analyzing image from URL: {image_url}")
    try:
        result = get_client().infer_url(image_url)
        detections = result.get("detections", [])
        
        # Format response for LLM consumption
        if not detections:
            return {
                "status": "success",
                "message": "No objects detected in the image",
                "detections": []
            }
        
        summary = []
        for d in detections:
            summary.append(f"- {d['label']} (confidence: {d['confidence']:.1%})")
        
        return {
            "status": "success",
            "message": f"Detected {len(detections)} object(s):\n" + "\n".join(summary),
            "detections": detections,
            "inference_time_ms": result.get("inference_time_ms")
        }
    except Exception as e:
        logger.exception("Error analyzing image")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def analyze_image_base64(image_base64: str, filename: str = "image.jpg") -> dict:
    """
    Analyze a base64-encoded image and detect objects.
    
    Args:
        image_base64: Base64-encoded image data
        filename: Original filename (optional, for format detection)
        
    Returns:
        Detection results with bounding boxes, class labels, and confidence scores
    """
    logger.info("Analyzing base64 image")
    try:
        result = get_client().infer_base64(image_base64, filename)
        detections = result.get("detections", [])
        
        if not detections:
            return {
                "status": "success",
                "message": "No objects detected in the image",
                "detections": []
            }
        
        summary = []
        for d in detections:
            summary.append(f"- {d['label']} (confidence: {d['confidence']:.1%})")
        
        return {
            "status": "success",
            "message": f"Detected {len(detections)} object(s):\n" + "\n".join(summary),
            "detections": detections,
            "inference_time_ms": result.get("inference_time_ms")
        }
    except Exception as e:
        logger.exception("Error analyzing image")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def analyze_with_filter(image_url: str, filter_name: str) -> dict:
    """
    Analyze an image using a specific detection filter.
    
    Filters can include/exclude specific object classes or set minimum confidence thresholds.
    
    Args:
        image_url: URL to the image to analyze
        filter_name: Name of the filter to apply (use list_filters to see available filters)
        
    Returns:
        Filtered detection results
    """
    logger.info(f"Analyzing image with filter '{filter_name}'")
    try:
        # Download image and convert to base64
        import httpx
        import base64
        
        img_response = httpx.get(image_url, timeout=30.0)
        img_response.raise_for_status()
        image_base64 = base64.b64encode(img_response.content).decode()
        
        result = get_client().infer_filtered(image_base64, filter_name)
        detections = result.get("detections", [])
        
        if not detections:
            return {
                "status": "success",
                "message": f"No objects matching filter '{filter_name}' detected",
                "filter_applied": filter_name,
                "detections": []
            }
        
        summary = []
        for d in detections:
            summary.append(f"- {d['label']} (confidence: {d['confidence']:.1%})")
        
        return {
            "status": "success",
            "message": f"Detected {len(detections)} object(s) with filter '{filter_name}':\n" + "\n".join(summary),
            "filter_applied": filter_name,
            "detections": detections
        }
    except Exception as e:
        logger.exception("Error analyzing image with filter")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def list_filters() -> dict:
    """
    List all available detection filters.
    
    Filters can be used to include/exclude specific object classes
    or set minimum confidence thresholds.
    
    Returns:
        Dictionary of available filters with their configurations
    """
    logger.info("Listing filters")
    try:
        filters = get_client().list_filters()
        
        if not filters:
            return {
                "status": "success",
                "message": "No filters configured. Use create_filter to add one.",
                "filters": {}
            }
        
        summary = []
        for name, config in filters.items():
            include = config.get("include_classes", [])
            exclude = config.get("exclude_classes", [])
            conf = config.get("min_confidence", 0.5)
            
            desc = f"- {name}: "
            if include:
                desc += f"include={include} "
            if exclude:
                desc += f"exclude={exclude} "
            desc += f"min_conf={conf}"
            summary.append(desc)
        
        return {
            "status": "success",
            "message": "Available filters:\n" + "\n".join(summary),
            "filters": filters
        }
    except Exception as e:
        logger.exception("Error listing filters")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def create_filter(
    name: str,
    include_classes: list[str] | None = None,
    exclude_classes: list[str] | None = None,
    min_confidence: float = 0.5
) -> dict:
    """
    Create a new detection filter.
    
    Args:
        name: Unique name for the filter
        include_classes: Only detect these classes (empty = all classes)
        exclude_classes: Exclude these classes from detection
        min_confidence: Minimum confidence threshold (0.0-1.0)
        
    Returns:
        Confirmation of filter creation
        
    Example:
        create_filter("vehicles", include_classes=["car", "truck", "bus"])
        create_filter("no_people", exclude_classes=["person"])
    """
    logger.info(f"Creating filter: {name}")
    try:
        result = get_client().create_filter(
            name=name,
            include_classes=include_classes,
            exclude_classes=exclude_classes,
            min_confidence=min_confidence
        )
        return {
            "status": "success",
            "message": f"Filter '{name}' created successfully",
            "filter": result
        }
    except Exception as e:
        logger.exception("Error creating filter")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def delete_filter(name: str) -> dict:
    """
    Delete a detection filter.
    
    Args:
        name: Name of the filter to delete
        
    Returns:
        Confirmation of deletion
    """
    logger.info(f"Deleting filter: {name}")
    try:
        get_client().delete_filter(name)
        return {
            "status": "success",
            "message": f"Filter '{name}' deleted successfully"
        }
    except Exception as e:
        logger.exception("Error deleting filter")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def list_models() -> dict:
    """
    List available object detection models.
    
    Returns:
        List of model bundles with their metadata
    """
    logger.info("Listing models")
    try:
        models = get_client().list_models()
        
        if not models:
            return {
                "status": "success",
                "message": "No models found in the models directory",
                "models": []
            }
        
        summary = []
        for m in models:
            name = m.get("name", "unknown")
            version = m.get("version", "?")
            active = " (active)" if m.get("active") else ""
            summary.append(f"- {name} v{version}{active}")
        
        return {
            "status": "success",
            "message": "Available models:\n" + "\n".join(summary),
            "models": models
        }
    except Exception as e:
        logger.exception("Error listing models")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def activate_model(bundle_path: str) -> dict:
    """
    Activate a specific model for inference.
    
    Args:
        bundle_path: Path to the model bundle (e.g., "demo/v1")
        
    Returns:
        Confirmation of model activation
    """
    logger.info(f"Activating model: {bundle_path}")
    try:
        result = get_client().activate_model(bundle_path)
        return {
            "status": "success",
            "message": f"Model '{bundle_path}' activated successfully",
            "result": result
        }
    except Exception as e:
        logger.exception("Error activating model")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def get_system_status() -> dict:
    """
    Get the current status of the Vision system.
    
    Returns:
        System health, model info, and watcher status
    """
    logger.info("Getting system status")
    try:
        client = get_client()
        
        health = client.health()
        
        try:
            watcher = client.get_watcher_status()
        except Exception:
            watcher = {"enabled": False}
        
        return {
            "status": "success",
            "health": health,
            "watcher": watcher,
            "message": f"System healthy. Model loaded: {health.get('model_loaded', False)}. "
                      f"Watcher enabled: {watcher.get('enabled', False)}"
        }
    except Exception as e:
        logger.exception("Error getting system status")
        return {"status": "error", "message": str(e)}


# ============================================================================
# Integration Management Tools
# ============================================================================

@mcp.tool()
def get_integrations_status() -> dict:
    """
    Get status of all integrations (OPC UA, MQTT, Webhook).
    
    Returns:
        Status and configuration of each integration
    """
    logger.info("Getting integrations status")
    try:
        result = get_client().get_integrations()
        
        opcua = result.get("opcua", {})
        mqtt = result.get("mqtt", {})
        webhook = result.get("webhook", {})
        
        summary_parts = []
        
        # OPC UA status
        if opcua.get("running"):
            summary_parts.append(f"OPC UA: Running on port {opcua.get('port')}")
        elif opcua.get("enabled"):
            summary_parts.append("OPC UA: Enabled but not running")
        else:
            summary_parts.append("OPC UA: Disabled")
        
        # MQTT status
        if mqtt.get("configured"):
            summary_parts.append(f"MQTT: Configured ({mqtt.get('broker')}:{mqtt.get('port')})")
        else:
            summary_parts.append("MQTT: Not configured")
        
        # Webhook status
        if webhook.get("configured"):
            summary_parts.append(f"Webhook: Configured ({webhook.get('url')})")
        else:
            summary_parts.append("Webhook: Not configured")
        
        return {
            "status": "success",
            "message": " | ".join(summary_parts),
            "integrations": result
        }
    except Exception as e:
        logger.exception("Error getting integrations status")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def configure_opcua(
    enabled: bool | None = None,
    port: int | None = None,
    update_interval_ms: int | None = None
) -> dict:
    """
    Configure OPC UA server settings.
    
    Args:
        enabled: Enable or disable the OPC UA server
        port: Server port (default 4840)
        update_interval_ms: How often to update nodes in ms (0 = immediate)
        
    Returns:
        Updated integration status
    """
    logger.info(f"Configuring OPC UA: enabled={enabled}, port={port}, interval={update_interval_ms}")
    try:
        result = get_client().update_integrations(
            opcua_enabled=enabled,
            opcua_port=port,
            opcua_update_interval_ms=update_interval_ms
        )
        
        opcua = result.get("opcua", {})
        running = "running" if opcua.get("running") else "stopped"
        
        return {
            "status": "success",
            "message": f"OPC UA configured: {running} on port {opcua.get('port')}",
            "opcua": opcua
        }
    except Exception as e:
        logger.exception("Error configuring OPC UA")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def configure_mqtt(
    broker: str | None = None,
    port: int | None = None,
    topic: str | None = None,
    username: str | None = None,
    password: str | None = None
) -> dict:
    """
    Configure MQTT client settings for publishing detection results.
    
    Args:
        broker: MQTT broker hostname
        port: Broker port (default 1883)
        topic: Topic to publish results to (default 'vision/results')
        username: Username for authentication (optional)
        password: Password for authentication (optional)
        
    Returns:
        Updated integration status
    """
    logger.info(f"Configuring MQTT: broker={broker}, port={port}, topic={topic}")
    try:
        result = get_client().update_integrations(
            mqtt_broker=broker,
            mqtt_port=port,
            mqtt_topic=topic,
            mqtt_username=username,
            mqtt_password=password
        )
        
        mqtt = result.get("mqtt", {})
        
        if mqtt.get("configured"):
            msg = f"MQTT configured: {mqtt.get('broker')}:{mqtt.get('port')} topic={mqtt.get('topic')}"
        else:
            msg = "MQTT not configured (no broker specified)"
        
        return {
            "status": "success",
            "message": msg,
            "mqtt": mqtt
        }
    except Exception as e:
        logger.exception("Error configuring MQTT")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def configure_webhook(
    url: str | None = None,
    headers: str | None = None
) -> dict:
    """
    Configure webhook for pushing detection results.
    
    Args:
        url: Target webhook URL to POST results to
        headers: JSON string of custom HTTP headers (optional)
        
    Returns:
        Updated integration status
        
    Example:
        configure_webhook(url="https://api.example.com/vision-results")
        configure_webhook(url="https://api.example.com/results", headers='{"Authorization": "Bearer token123"}')
    """
    logger.info(f"Configuring webhook: url={url}")
    try:
        result = get_client().update_integrations(
            webhook_url=url,
            webhook_headers=headers
        )
        
        webhook = result.get("webhook", {})
        
        if webhook.get("configured"):
            msg = f"Webhook configured: {webhook.get('url')}"
        else:
            msg = "Webhook not configured (no URL specified)"
        
        return {
            "status": "success",
            "message": msg,
            "webhook": webhook
        }
    except Exception as e:
        logger.exception("Error configuring webhook")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def test_webhook() -> dict:
    """
    Send a test message to the configured webhook URL.
    
    Returns:
        Test result with success or error message
    """
    logger.info("Testing webhook")
    try:
        result = get_client().test_webhook()
        return {
            "status": "success",
            "message": f"Webhook test sent to {result.get('url')}",
            "result": result
        }
    except Exception as e:
        logger.exception("Webhook test failed")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def test_mqtt() -> dict:
    """
    Send a test message to the configured MQTT broker.
    
    Returns:
        Test result with success or error message
    """
    logger.info("Testing MQTT")
    try:
        result = get_client().test_mqtt()
        return {
            "status": "success",
            "message": f"MQTT test published to {result.get('broker')} topic {result.get('topic')}",
            "result": result
        }
    except Exception as e:
        logger.exception("MQTT test failed")
        return {"status": "error", "message": str(e)}


# ============================================================================
# Resources
# ============================================================================

@mcp.resource("vision://status")
def get_status_resource() -> str:
    """Current Vision system status."""
    try:
        health = get_client().health()
        return f"Vision System: {'healthy' if health.get('status') == 'ok' else 'unhealthy'}"
    except Exception as e:
        return f"Vision System: error - {e}"


# ============================================================================
# Main entry point
# ============================================================================

def main():
    """Run the MCP server."""
    logger.info("Starting Vision MCP Server...")
    logger.info(f"Vision API URL: {os.getenv('VISION_API_URL', 'http://runner:8000')}")
    
    # Run with SSE transport for network access
    transport = os.getenv("MCP_TRANSPORT", "sse")
    port = int(os.getenv("MCP_PORT", "8080"))
    
    if transport == "sse":
        logger.info(f"Starting SSE transport on port {port}")
        mcp.run(transport="sse", port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
