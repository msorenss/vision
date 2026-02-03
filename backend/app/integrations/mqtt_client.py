import os
import json
import logging
import asyncio
from typing import Any

logger = logging.getLogger(__name__)

try:
    import aiomqtt
except ImportError:
    aiomqtt = None
    logger.warning("aiomqtt not installed, MQTT integration disabled")

async def publish_results(data: dict[str, Any]) -> None:
    """Publish inference results to an MQTT broker.
    
    Reads configuration from environment:
    - VISION_MQTT_BROKER: Broker hostname (required to enable)
    - VISION_MQTT_PORT: Broker port (default 1883)
    - VISION_MQTT_TOPIC: Topic to publish to (default 'vision/results')
    - VISION_MQTT_USERNAME: Username (optional)
    - VISION_MQTT_PASSWORD: Password (optional)
    """
    if not aiomqtt:
        return

    broker = os.getenv("VISION_MQTT_BROKER")
    if not broker:
        return

    port = int(os.getenv("VISION_MQTT_PORT", "1883"))
    topic = os.getenv("VISION_MQTT_TOPIC", "vision/results")
    username = os.getenv("VISION_MQTT_USERNAME")
    password = os.getenv("VISION_MQTT_PASSWORD")

    try:
        async with aiomqtt.Client(
            hostname=broker,
            port=port,
            username=username,
            password=password,
            timeout=5
        ) as client:
            payload = json.dumps(data)
            await client.publish(topic, payload)
            logger.info(f"Published results to MQTT topic {topic}")
            
    except Exception as e:
        logger.error(f"Failed to publish to MQTT: {e}")
