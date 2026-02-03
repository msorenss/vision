import os
import json
import logging
import aiohttp
from typing import Any

logger = logging.getLogger(__name__)

async def send_webhook(data: dict[str, Any]) -> None:
    """Send inference results to a configured webhook URL.
    
    Reads configuration from environment variables:
    - VISION_WEBHOOK_URL: Target URL (required to enable)
    - VISION_WEBHOOK_HEADERS: JSON string of headers (optional)
    """
    url = os.getenv("VISION_WEBHOOK_URL")
    if not url:
        return

    headers_str = os.getenv("VISION_WEBHOOK_HEADERS", "{}")
    try:
        headers = json.loads(headers_str)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in VISION_WEBHOOK_HEADERS")
        headers = {}

    # Set default content type if not present
    if "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers, timeout=5) as resp:
                if resp.status >= 400:
                    logger.error(f"Webhook failed with status {resp.status}: {await resp.text()}")
                else:
                    logger.info(f"Webhook sent successfully to {url}")
    except Exception as e:
        logger.error(f"Failed to send webhook: {e}")
