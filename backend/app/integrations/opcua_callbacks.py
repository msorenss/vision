import logging
import asyncio
import os
from pathlib import Path
from app.integrations.opcua_server import server_instance
from app.inference.engine import get_engine, reset_engine
from typing import Optional

logger = logging.getLogger(__name__)

def _models_dir() -> Path:
    # Logic duplicated from routes.py, could be shared util
    env_path = os.getenv("VISION_MODELS_DIR")
    if env_path: return Path(env_path).resolve()
    docker = Path("/models")
    if docker.exists(): return docker
    return Path(__file__).resolve().parents[3] / "models"

async def setup_opcua_callbacks():
    """Register callbacks for OPC UA Server methods."""
    
    async def on_select_model(model_name: str) -> bool:
        logger.info(f"OPC UA Callback: SelectModel '{model_name}'")
        engine = get_engine()
        
        # 1. Check if model_name is a full path?
        if "/" in model_name or "\\" in model_name:
             if os.path.exists(model_name):
                 os.environ["VISION_MODEL_PATH"] = model_name
                 reset_engine()
                 return True
        
        # 2. Search in models dir for bundle name matching model_name
        # structure: models/<name>/<version>/model.onnx
        # Input could be "demo" (find latets) or "demo v1"
        root = _models_dir()
        candidate = None
        
        for name_dir in root.iterdir():
            if not name_dir.is_dir(): continue
            # If exact match on bundle name
            if name_dir.name == model_name:
                # Find latest version
                versions = sorted([v for v in name_dir.iterdir() if v.is_dir()], key=lambda x: x.name, reverse=True)
                if versions:
                    model_file = versions[0] / "model.onnx"
                    if model_file.exists():
                        candidate = model_file
                        break
            
            # Or assume incoming name is "name version" or "name/version"
            for ver_dir in name_dir.iterdir():
                if not ver_dir.is_dir(): continue
                # Match "demo v1"
                combo = f"{name_dir.name} {ver_dir.name}"
                combo2 = f"{name_dir.name}/{ver_dir.name}"
                if model_name == combo or model_name == combo2:
                     model_file = ver_dir / "model.onnx"
                     if model_file.exists():
                         candidate = model_file
                         break
            if candidate: break
            
        if candidate:
            logger.info(f"Found model: {candidate}")
            os.environ["VISION_MODEL_PATH"] = str(candidate)
            reset_engine()
            return True
            
        logger.warning(f"SelectModel: Could not find model '{model_name}'")
        return False

    async def on_start_single_job():
        logger.info("OPC UA Callback: StartSingleJob")
        # In a real system, this would trigger camera acquisition.
        # Here we verify the engine is ready.
        engine = get_engine()
        if not engine.loaded:
            logger.warning("Engine not loaded")
            # We could trigger a reload here?
            return 
            
        # We can't easily trigger "predict" without an image.
        # But we can log that we Started.
        pass

    async def on_stop():
        logger.info("OPC UA Callback: Stop")
        # Logic to stop continuous mode if we had one
        pass

    server_instance.register_callback("select_model", on_select_model)
    server_instance.register_callback("start_job", on_start_single_job)
    server_instance.register_callback("stop", on_stop)
    
    logger.info("OPC UA Callbacks registered")
