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
    
    # ============ Integrations ============
    
    def get_integrations(self) -> dict[str, Any]:
        """Get status of all integrations (OPC UA, MQTT, Webhook)."""
        response = self.client.get("/api/v1/integrations")
        response.raise_for_status()
        return response.json()
    
    def update_integrations(
        self,
        opcua_enabled: bool | None = None,
        opcua_port: int | None = None,
        opcua_update_interval_ms: int | None = None,
        mqtt_broker: str | None = None,
        mqtt_port: int | None = None,
        mqtt_topic: str | None = None,
        mqtt_username: str | None = None,
        mqtt_password: str | None = None,
        webhook_url: str | None = None,
        webhook_headers: str | None = None,
    ) -> dict[str, Any]:
        """Update integration settings at runtime."""
        payload = {}
        
        if opcua_enabled is not None:
            payload["opcua_enabled"] = opcua_enabled
        if opcua_port is not None:
            payload["opcua_port"] = opcua_port
        if opcua_update_interval_ms is not None:
            payload["opcua_update_interval_ms"] = opcua_update_interval_ms
        
        if mqtt_broker is not None:
            payload["mqtt_broker"] = mqtt_broker
        if mqtt_port is not None:
            payload["mqtt_port"] = mqtt_port
        if mqtt_topic is not None:
            payload["mqtt_topic"] = mqtt_topic
        if mqtt_username is not None:
            payload["mqtt_username"] = mqtt_username
        if mqtt_password is not None:
            payload["mqtt_password"] = mqtt_password
        
        if webhook_url is not None:
            payload["webhook_url"] = webhook_url
        if webhook_headers is not None:
            payload["webhook_headers"] = webhook_headers
        
        response = self.client.post("/api/v1/integrations", json=payload)
        response.raise_for_status()
        return response.json()
    
    def test_webhook(self) -> dict[str, Any]:
        """Send a test message to the configured webhook."""
        response = self.client.post("/api/v1/integrations/test/webhook")
        response.raise_for_status()
        return response.json()
    
    def test_mqtt(self) -> dict[str, Any]:
        """Send a test message to the configured MQTT broker."""
        response = self.client.post("/api/v1/integrations/test/mqtt")
        response.raise_for_status()
        return response.json()
