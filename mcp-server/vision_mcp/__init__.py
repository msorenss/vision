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
    
    if transport == "sse":
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
