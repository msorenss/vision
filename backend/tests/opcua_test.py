import asyncio
import sys
import json
import urllib.request
from asyncua import Client, ua

class SubHandler:
    def event_notification(self, event):
        print(f"EVENT RECEIVED: {event}")
        sys.stdout.flush()

async def main():
    try:
        url = "opc.tcp://localhost:4840/freeopcua/server/"
        print(f"Connecting to {url}...")
        sys.stdout.flush()
        
        async with Client(url=url) as client:
            print("Connected!")
            sys.stdout.flush()
            
            idx_mv = await client.get_namespace_index("http://opcfoundation.org/UA/MachineVision")
            obj_mv = await client.nodes.objects.get_child([f"{idx_mv}:VisionSystem"])
            
            # Subscribe
            print("Creating subscription...")
            sys.stdout.flush()
            handler = SubHandler()
            sub = await client.create_subscription(500, handler)
            handle = await sub.subscribe_events(obj_mv)
            print("Subscribed!")
            sys.stdout.flush()
            
            print("Waiting for events...")
            sys.stdout.flush()

            # Trigger HTTP
            try:
                print("Triggering HTTP inference...")
                sys.stdout.flush()
                # Run blocking urllib in executor or just block (it's fine for this test)
                req = urllib.request.Request("http://localhost:8000/api/v1/demo/infer/filtered?name=bus.jpg")
                with urllib.request.urlopen(req) as response:
                    print(f"HTTP Status: {response.status}")
                    body = response.read()
                    print(f"HTTP Body len: {len(body)}")
            except Exception as e:
                print(f"HTTP Trigger failed: {e}")
            sys.stdout.flush()

            # Test SelectModel
            print("Calling SelectModel('demo v1')...")
            sys.stdout.flush()
            try:
                # Find SelectModel method
                method_select = await obj_mv.get_child([f"{idx_mv}:SelectModel"])
                # Call it
                res = await obj_mv.call_method(method_select, "demo v1")
                print(f"SelectModel Result: {res}")
            except Exception as e:
                print(f"SelectModel Error: {e}")
            sys.stdout.flush()

            await asyncio.sleep(5)
            print("Done waiting.")
            sys.stdout.flush()

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(main())
