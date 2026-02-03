import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Any
from enum import IntEnum

logger = logging.getLogger(__name__)

try:
    from asyncua import Server, ua, uamethod
except ImportError:
    Server = None
    logger.warning("asyncua not installed, OPC UA integration disabled")

# States according to simplified OM
class VisionState(IntEnum):
    Preoperational = 0
    Ready = 1
    SingleExecution = 2
    ContinuousExecution = 3
    Error = 4

class VisionOpcUaServer:
    def __init__(self):
        self.server = None
        self.running = False
        self.vision_system = None
        self.vsm = None
        self.state_node = None # Actual 40100 node (String/LocalizedText)
        self.compat_state_node = None # Legacy Int
        self.result_mgmt = None
        self.last_result_node = None
        self.counter_node = None
        self.model_node = None
        
        self.namespace_idx = 0
        self.custom_idx = 0
        self._current_state = VisionState.Preoperational
        self.evt_result_ready_type = None
        self.alarm_node = None
        self.callbacks = {}

    def register_callback(self, name: str, func):
        self.callbacks[name] = func

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
            
            # --- NAMESPACES ---
            # 1. Official OPC 40100 Namespace
            ns_mv = await self.server.register_namespace("http://opcfoundation.org/UA/MachineVision")
            # 2. Legacy/Custom Namespace
            ns_legacy = await self.server.register_namespace("http://volvocars.com/vision")
            
            objects = self.server.nodes.objects
            
            # --- LEGACY IMPLEMENTATION (Simple & PLC Friendly) ---
            # Object: VisionSystem (Legacy)
            self.vs_legacy = await objects.add_object(ns_legacy, "VisionSystem-Legacy")
            
            # Legacy Variables
            self.compat_state_node = await self.vs_legacy.add_variable(ns_legacy, "State", VisionState.Preoperational.value)
            self.counter_node = await self.vs_legacy.add_variable(ns_legacy, "DisplayCount", 0)
            self.model_node = await self.vs_legacy.add_variable(ns_legacy, "ActiveModel", "Unknown")
            self.last_result_node = await self.vs_legacy.add_variable(ns_legacy, "LastResult", "{}")
            
            # Expanded Result Nodes (Primary Detection)
            # These allow a PLC to easily read the "best" detection without parsing JSON
            self.res_class_node = await self.vs_legacy.add_variable(ns_legacy, "Result_Class", "")
            self.res_score_node = await self.vs_legacy.add_variable(ns_legacy, "Result_Score", 0.0)
            self.res_box_node = await self.vs_legacy.add_variable(ns_legacy, "Result_Box", "[]") # JSON string or array
            
            # --- OPC 40100 IMPLEMENTATION (Standard Compliant) ---
            # Object: VisionSystem (Standard)
            self.vs_40100 = await objects.add_object(ns_mv, "VisionSystem")
            # Enable Event Notifications
            await self.vs_40100.set_event_notifier([ua.EventNotifier.SubscribeToEvents])
            
            # Component: VisionStateMachine
            self.vsm = await self.vs_40100.add_object(ns_mv, "VisionStateMachine")
            self.state_node = await self.vsm.add_variable(ns_mv, "CurrentState", "Preoperational")
            
            # Component: ResultManagement
            self.result_mgmt = await self.vs_40100.add_object(ns_mv, "ResultManagement")
            
            # Methods (40100)
            inargs = []
            outargs = [ua.Argument(Name="JobId", DataType=ua.NodeId(ua.ObjectIds.String), ValueRank=-1, ArrayDimensions=[])]
            
            # StartSingleJob
            await self.vs_40100.add_method(ns_mv, "StartSingleJob", self.method_start_single_job, inargs, outargs)
            
            # StartContinuous
            await self.vs_40100.add_method(ns_mv, "StartContinuous", self.method_start_continuous, inargs, outargs)
            
            # Stop
            await self.vs_40100.add_method(ns_mv, "Stop", self.method_stop, inargs, [])

            # Abort
            await self.vs_40100.add_method(ns_mv, "Abort", self.method_abort, inargs, [])
            
            # Reset
            await self.vs_40100.add_method(ns_mv, "Reset", self.method_reset, inargs, [])

            # --- CONFIG METHODS (Volvo Standard) ---
            # SelectModel
            model_args = [ua.Argument(Name="ModelName", DataType=ua.NodeId(ua.ObjectIds.String), ValueRank=-1, ArrayDimensions=[])]
            out_res = [ua.Argument(Name="Result", DataType=ua.NodeId(ua.ObjectIds.String), ValueRank=-1, ArrayDimensions=[])]
            await self.vs_40100.add_method(ns_mv, "SelectModel", self.method_select_model, model_args, out_res)

            # --- EVENTS (40100 Compliance) ---
            # Define ResultReadyEventType
            # Note: create_custom_event_type is a helper. ResultManagementType should ideally host this.
            self.evt_result_ready_type = await self.server.create_custom_event_type(
                ns_mv, "ResultReadyEventType", ua.ObjectIds.BaseEventType,
                [
                    ("ResultId", ua.VariantType.String),
                    ("JobId", ua.VariantType.String),
                    ("ProcessingTimes", ua.VariantType.Double),
                ]
            )
            
            # --- ALARMS ---
            # Create a simplified SystemErrorAlarm
            # We use an object that represents the alarm condition
            self.alarm_node = await self.vs_40100.add_object(ns_mv, "SystemErrorAlarm", ua.ObjectIds.AlarmConditionType)
            await self.alarm_node.set_event_notifier([ua.EventNotifier.SubscribeToEvents])
            # Note: Full Alarm implementation is complex. We will simulate it by triggering events from this node.

            # Start Server
            await self.server.start()
            self.running = True
            
            # Transition to Ready
            await self.set_state(VisionState.Ready)
            
            logger.info(f"OPC UA Server started at {endpoint} (Full Industrial Capable)")
            
        except Exception as e:
            logger.error(f"Failed to start OPC UA Server: {e}")
            self.running = False

    # --- STATE MACHINE METHODS ---

    @uamethod
    async def method_start_single_job(self, parent):
        logger.info("OPC UA: StartSingleJob")
        if self._current_state != VisionState.Ready:
             logger.warning(f"StartSingleJob failed: State is {self._current_state.name}")
             return ""

        # Trigger internal callback if registered
        if "start_job" in self.callbacks:
             # run callback in background to not block OPC UA
             asyncio.create_task(self.callbacks["start_job"]())
        else:
             # Simulated fallback
             asyncio.create_task(self._simulate_job(single=True))
             
        job_id = f"job-{asyncio.get_event_loop().time()}"
        return job_id

    @uamethod
    async def method_start_continuous(self, parent):
        logger.info("OPC UA: StartContinuous")
        if self._current_state != VisionState.Ready:
             pass 

        job_id = f"cont-{asyncio.get_event_loop().time()}"
        await self.set_state(VisionState.ContinuousExecution)
        
        if "start_continuous" in self.callbacks:
            asyncio.create_task(self.callbacks["start_continuous"]())
            
        return job_id

    @uamethod
    async def method_stop(self, parent):
        logger.info("OPC UA: Stop")
        if self._current_state == VisionState.ContinuousExecution:
            await self.set_state(VisionState.Ready)
            if "stop" in self.callbacks:
                asyncio.create_task(self.callbacks["stop"]())

    @uamethod
    async def method_abort(self, parent):
        logger.info("OPC UA: Abort")
        await self.set_state(VisionState.Ready)
        if "abort" in self.callbacks:
            asyncio.create_task(self.callbacks["abort"]())

    @uamethod
    async def method_reset(self, parent):
        logger.info("OPC UA: Reset")
        if self._current_state == VisionState.Error:
            await self.set_state(VisionState.Ready)
            if "reset" in self.callbacks:
                asyncio.create_task(self.callbacks["reset"]())

    @uamethod
    async def method_select_model(self, parent, model_name):
        logger.info(f"OPC UA: SelectModel({model_name})")
        mname = model_name
        if hasattr(model_name, "Value"):
            mname = model_name.Value
            
        if "select_model" in self.callbacks:
             try:
                 # Call callback
                 # We expect this to be async or we wrap it
                 res = await self.callbacks["select_model"](str(mname))
                 return "OK" if res else "Failed"
             except Exception as e:
                 logger.error(f"SelectModel failed: {e}")
                 return f"Error: {e}"
        return "No backend handler"

    async def _simulate_job(self, single=True):
        await self.set_state(VisionState.SingleExecution)
        # Simulate inference time
        await asyncio.sleep(0.5) 
        # In a real scenario, this would wait for the result
        if single:
            await self.set_state(VisionState.Ready)

    # ... update_result ...


    async def update_result(self, result: dict, model_name: str):
        if not self.running:
            return

        try:
            # 1. Update Legacy JSON
            json_res = json.dumps(result)
            if self.last_result_node:
                await self.last_result_node.write_value(json_res)
            
            # 2. Update Legacy Scalars (Primary Detection)
            # Find detection with highest confidence
            detections = result.get("detections", [])
            primary = None
            if detections:
                # Assuming sorted by score, otherwise sort
                primary = max(detections, key=lambda x: x.get("score", 0))
            
            if primary:
                if self.res_class_node:
                    await self.res_class_node.write_value(primary.get("label", "Unknown"))
                if self.res_score_node:
                    await self.res_score_node.write_value(primary.get("score", 0.0))
                if self.res_box_node:
                    await self.res_box_node.write_value(json.dumps(primary.get("box", {})))
            else:
                # Clear values if no detection
                if self.res_class_node: await self.res_class_node.write_value("")
                if self.res_score_node: await self.res_score_node.write_value(0.0)
                if self.res_box_node: await self.res_box_node.write_value("{}")

            # 3. Update Counters & Model
            if self.counter_node:
                val = await self.counter_node.read_value()
                await self.counter_node.write_value(val + 1)
            
            if self.model_node:
                await self.model_node.write_value(model_name)
            
            # 4. Trigger 40100 ResultReadyEvent
            if self.evt_result_ready_type:
                # Event source should be VisionSystem or ResultManagement
                # Using VisionSystem (vs_40100) as source
                my_event = await self.server.get_event_generator(self.evt_result_ready_type, self.vs_40100)
                
                # Standard Event Fields
                my_event.event.Message = ua.LocalizedText("Result Ready")
                my_event.event.Severity = 100
                # my_event.event.Time = datetime.utcnow() # BaseEventType handles this automatically usually

                # Custom Fields
                # Generate a simple ResultId (e.g. timestamp + counter)
                res_id = f"res-{datetime.utcnow().timestamp()}"
                my_event.event.ResultId = res_id
                
                # JobId (pass through if available in result, else manual)
                my_event.event.JobId = result.get("jobId", "job-manual")
                
                # ProcessingTimes
                my_event.event.ProcessingTimes = result.get("inference_time", 0.0)

                await my_event.trigger()
                logger.debug(f"Triggered ResultReadyEvent: {res_id}")
            
        except Exception as e:
            logger.error(f"Error updating OPC UA nodes: {e}")

    async def set_state(self, state: VisionState):
        old_state = self._current_state
        self._current_state = state
        if not self.running:
            return
        
        # Helper to trigger alarm events
        async def trigger_alarm(activate: bool, message: str):
            if not self.alarm_node: return
            try:
                # Get the event generator from the AlarmConditionType
                gen = await self.server.get_event_generator(self.alarm_node)
                gen.event.Message = ua.LocalizedText(message)
                gen.event.Severity = 1000 if activate else 0
                gen.event.Retain = activate
                gen.event.ConditionName = "SystemError"
                # gen.event.EnabledState = ... complex types often need simplifications
                await gen.trigger()
            except Exception as e:
                logger.warning(f"Failed to trigger alarm: {e}")

        try:
            # Handle Alarms based on state
            if state == VisionState.Error and old_state != VisionState.Error:
                await trigger_alarm(True, "System entered Error State")
            elif old_state == VisionState.Error and state != VisionState.Error:
                await trigger_alarm(False, "System recovered from Error")

            # Update 40100 State (String)
            if self.state_node:
                await self.state_node.write_value(state.name)
            
            # Update Legacy State (Int)
            if self.compat_state_node:
                await self.compat_state_node.write_value(state.value)
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
