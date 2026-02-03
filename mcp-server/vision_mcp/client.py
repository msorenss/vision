"""
Vision MCP Client - HTTP client for Vision Runner API
"""
import httpx
from typing import Any
import base64
import os


class VisionClient:
    """Client for interacting with Vision Runner API."""
    
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or os.getenv("VISION_API_URL", "http://runner:8000")
        self.client = httpx.Client(base_url=self.base_url, timeout=60.0)
    
    def health(self) -> dict[str, Any]:
        """Check API health status."""
        response = self.client.get("/health")
        response.raise_for_status()
        return response.json()
    
    def infer_url(self, image_url: str) -> dict[str, Any]:
        """Run inference on image from URL."""
        # Download image first
        img_response = httpx.get(image_url, timeout=30.0)
        img_response.raise_for_status()
        
        files = {"image": ("image.jpg", img_response.content, "image/jpeg")}
        response = self.client.post("/api/v1/infer", files=files)
        response.raise_for_status()
        return response.json()
    
    def infer_base64(self, image_base64: str, filename: str = "image.jpg") -> dict[str, Any]:
        """Run inference on base64-encoded image."""
        image_bytes = base64.b64decode(image_base64)
        files = {"image": (filename, image_bytes, "image/jpeg")}
        response = self.client.post("/api/v1/infer", files=files)
        response.raise_for_status()
        return response.json()
    
    def infer_filtered(self, image_base64: str, filter_name: str) -> dict[str, Any]:
        """Run inference with a specific filter."""
        image_bytes = base64.b64decode(image_base64)
        files = {"image": ("image.jpg", image_bytes, "image/jpeg")}
        response = self.client.post(
            "/api/v1/infer/filtered",
            files=files,
            params={"filter": filter_name}
        )
        response.raise_for_status()
        return response.json()
    
    def list_models(self) -> list[dict[str, Any]]:
        """List available model bundles."""
        response = self.client.get("/api/v1/models")
        response.raise_for_status()
        return response.json()
    
    def activate_model(self, bundle_path: str) -> dict[str, Any]:
        """Activate a specific model bundle."""
        response = self.client.post(
            "/api/v1/models/activate",
            json={"bundle_path": bundle_path}
        )
        response.raise_for_status()
        return response.json()
    
    def list_filters(self) -> dict[str, Any]:
        """List all detection filters."""
        response = self.client.get("/api/v1/filters")
        response.raise_for_status()
        return response.json()
    
    def create_filter(
        self,
        name: str,
        include_classes: list[str] | None = None,
        exclude_classes: list[str] | None = None,
        min_confidence: float = 0.5
    ) -> dict[str, Any]:
        """Create a new detection filter."""
        filter_config = {
            "name": name,
            "enabled": True,
            "include_classes": include_classes or [],
            "exclude_classes": exclude_classes or [],
            "min_confidence": min_confidence
        }
        response = self.client.post("/api/v1/filters", json=filter_config)
        response.raise_for_status()
        return response.json()
    
    def delete_filter(self, name: str) -> dict[str, Any]:
        """Delete a detection filter."""
        response = self.client.delete(f"/api/v1/filters/{name}")
        response.raise_for_status()
        return response.json()
    
    def get_watcher_status(self) -> dict[str, Any]:
        """Get watcher/auto-detection status."""
        response = self.client.get("/api/v1/watcher/status")
        response.raise_for_status()
        return response.json()
    
    def get_settings(self) -> dict[str, Any]:
        """Get current settings."""
        response = self.client.get("/api/v1/settings")
        response.raise_for_status()
        return response.json()
