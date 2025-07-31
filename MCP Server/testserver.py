import asyncio
import json
import websockets

async def handle_item_data(websocket):
    data = await websocket.recv()
    print(f"Received {len(data)} bytes of data from DIM.")
    try:
        items = json.loads(data)
    except json.JSONDecodeError as e:
        print(f"Error: Received invalid JSON data - {e}")
        return
    with open("items.json", "w") as f:
        json.dump(items, f, indent=2)
    print("Saved inventory data to items.json")

async def main():
    async with websockets.serve(handle_item_data, "localhost", 8765):
        print("Test server running on ws://localhost:8765 ...")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

