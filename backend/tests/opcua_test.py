import asyncio
from asyncua import Client

async def main():
    url = "opc.tcp://localhost:4840/freeopcua/server/"
    print(f"Connecting to {url}...")
    
    async with Client(url=url) as client:
        print("Connected!")
        
        # Get Namespace Indexes
        idx_mv = await client.get_namespace_index("http://opcfoundation.org/UA/MachineVision")
        idx_vision = await client.get_namespace_index("http://volvocars.com/vision")
        print(f"MachineVision NS Index: {idx_mv}")
        print(f"Vision NS Index: {idx_vision}")
        
        # Find Nodes
        # VisionSystem (40100)
        obj_mv = await client.nodes.objects.get_child([f"{idx_mv}:VisionSystem"])
        print(f"Found VisionSystem (40100): {obj_mv}")
        
        # Method
        method = await obj_mv.get_child([f"{idx_mv}:StartSingleJob"])
        print(f"Found StartSingleJob: {method}")
        
        # State Node (Legacy for easy checking)
        state_node = await client.nodes.objects.get_child([f"{idx_vision}:VisionSystem-Legacy", f"{idx_vision}:State"])
        print(f"Found Legacy State Node: {state_node}")
        
        val = await state_node.read_value()
        print(f"Initial State: {val} (Should be 1=Ready)")
        
        # Call Method
        print("Calling StartSingleJob...")
        res = await obj_mv.call_method(method)
        print(f"Method Result: {res}")
        
        # Check State immediately (should be 2=SingleExecution or back to 1)
        # Since it sleeps 0.5s, if we are fast we might catch it
        await asyncio.sleep(0.1)
        val = await state_node.read_value()
        print(f"State after 0.1s: {val} (Should be 2=SingleExecution)")
        
        await asyncio.sleep(1.0)
        val = await state_node.read_value()
        print(f"State after 1.0s: {val} (Should be 1=Ready)")

if __name__ == "__main__":
    asyncio.run(main())
