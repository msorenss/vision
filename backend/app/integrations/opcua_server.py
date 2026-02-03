import os
import json
import logging
import asyncio
from typing import Any

logger = logging.getLogger(__name__)

try:
    from asyncua import Server, ua
except ImportError:
    Server = None
    logger.warning("asyncua not installed, OPC UA integration disabled")

class VisionOpcUaServer:
    def __init__(self):
        self.server = None
        self.running = False
        self.vision_system = None
        self.state_node = None
        self.last_result_node = None
        self.counter_node = None
        self.model_node = None

    async def start(self):
        if not Server:
            return

        enabled = os.getenv("VISION_OPCUA_ENABLE", "0")
        if enabled != "1":
            return

        endpoint = os.getenv("VISION_OPCUA_ENDPOINT", "opc.tcp://0.0.0.0:4840/freeopcua/server/")
        
        try:
            self.server = Server()
            await self.server.init()
            self.server.set_endpoint(endpoint)
            self.server.set_server_name("Volvo Vision Server")
            
            # Setup Namespace
            idx = await self.server.register_namespace("http://volvocars.com/vision")
            
            # --- Object Model Setup ---
            objects = self.server.nodes.objects
            
            # 1. VisionSystem (Object)
            self.vision_system = await objects.add_object(idx, "VisionSystem")
            
            # 2. Basic Info
            self.model_node = await self.vision_system.add_variable(idx, "ActiveModel", "Unknown")
            
            # 3. State (0=Off, 1=Ready, 2=Processing, 3=Error)
            self.state_node = await self.vision_system.add_variable(idx, "State", 1)
            
            # 4. Results (Object)
            results_obj = await self.vision_system.add_object(idx, "Results")
            
            self.last_result_node = await results_obj.add_variable(idx, "LastResult", "{}")
            self.counter_node = await results_obj.add_variable(idx, "DisplayCount", 0)
            
            # Start Server
            await self.server.start()
            self.running = True
            logger.info(f"OPC UA Server started at {endpoint}")
            
        except Exception as e:
            logger.error(f"Failed to start OPC UA Server: {e}")
            self.running = False

    async def update_result(self, result: dict, model_name: str):
        if not self.running:
            return

        try:
            # Update state to Processing (transient, might be too fast to see)
            # await self.state_node.write_value(2) 
            
            # Update result
            await self.last_result_node.write_value(json.dumps(result))
            
            # Update counter
            val = await self.counter_node.read_value()
            await self.counter_node.write_value(val + 1)
            
            # Update model name
            current_model = await self.model_node.read_value()
            if current_model != model_name:
                await self.model_node.write_value(model_name)
                
            # Back to Ready
            # await self.state_node.write_value(1)
            
        except Exception as e:
            logger.error(f"Error updating OPC UA nodes: {e}")

    async def set_state(self, state: int):
        if self.running and self.state_node:
            try:
                await self.state_node.write_value(state)
            except Exception:
                pass

    async def stop(self):
        if self.running and self.server:
            try:
                await self.server.stop()
                logger.info("OPC UA Server stopped")
            except Exception as e:
                logger.error(f"Error stopping OPC UA Server: {e}")
            finally:
                self.running = False

# Singleton instance
server_instance = VisionOpcUaServer()
