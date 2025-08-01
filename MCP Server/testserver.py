from fastmcp import FastMCP
import subprocess, json, os, sys
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
                print(f"[DEBUG] Inventory response: {response}")
                print("Inventory Response:", response)
            except Exception as e:
                print(f"[ERROR] Failed to request inventory: {e}")



def getWeaponsSummary():
    weapons = []
    # Logic to populate weapons array
    # Example:
    # weapons.append({"name": "Sword", "damage": 10})
    return weapons

def getArmorSummary():
    armor = []
    # Logic to populate armor array
    # Example:
    # armor.append({"name": "Shield", "defense": 5})
    return armor

async def handleMessage(message, websocket):
    # Assuming message is a dict and websocket is a WebSocket connection
    if message.get('type') == 'ping':
        weapons = getWeaponsSummary()
        armor = getArmorSummary()
        await websocket.send(json.dumps({
            'type': 'pong',
            'weapons': weapons,
            'armor': armor
        }))


if __name__ == "__main__":
    async def start_all():
        server_task = asyncio.create_task(start_websocket_server())
        input_task = asyncio.create_task(handle_user_input())
        await asyncio.gather(server_task, input_task)

    try:
        asyncio.run(start_all())
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
