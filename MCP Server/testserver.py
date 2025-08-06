import json
import asyncio
from websocket_server import request_inventory, main as start_websocket_server




async def handle_user_input():
    while True:
        cmd = await asyncio.get_event_loop().run_in_executor(None, input, ">>> ")
        print(f"[DEBUG] Received command: {cmd.strip()}")
        if cmd.strip() == "ping":
            try:
                print("[DEBUG] Calling request_inventory...")
                response = await request_inventory()
                pretty_response = json.dumps(response, indent=2)
                print("[DEBUG] Inventory response (pretty):")
                print(pretty_response)
            except Exception as e:
                print(f"[ERROR] Failed to request inventory: {e}")




if __name__ == "__main__":
    async def start_all():
        server_task = asyncio.create_task(start_websocket_server())
        input_task = asyncio.create_task(handle_user_input())
        await asyncio.gather(server_task, input_task)

    try:
        asyncio.run(start_all())
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
