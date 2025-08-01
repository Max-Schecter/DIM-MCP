from fastmcp import FastMCP
import subprocess, json, os, sys
import asyncio
from websocket_server import request_inventory, main as start_websocket_server

# Create the MCP server object
mcp = FastMCP("Destiny MCP Server")

# Paths
SCRIPT_DIR = os.path.dirname(__file__)
MANIFEST_CACHE = os.path.join(SCRIPT_DIR, "manifest_cache")
WEAPONS_JSON = os.path.join(MANIFEST_CACHE, "weapons_output.json")
DESTINY_SCRIPT = os.path.join(SCRIPT_DIR, "destiny_api.py")


@mcp.tool
def get_weapons_inventory() -> dict:
    """
    Return the latest Destiny‑2 weapon inventory as JSON.

    Steps:
    1. Run destiny_api.py with the same Python interpreter and correct working dir.
    2. If it fails, surface stderr so we can see the real error in Claude.
    3. Load and return weapons_output.json.
    """
    # Ensure manifest cache directory exists
    os.makedirs(MANIFEST_CACHE, exist_ok=True)

    # Run the script using the same interpreter and ensure correct cwd
    proc = subprocess.run(
        [sys.executable, DESTINY_SCRIPT],
        cwd=SCRIPT_DIR,
        text=True,
        capture_output=True
    )

    if proc.returncode != 0:
        # Bubble up the real traceback for debugging in Claude
        raise RuntimeError(f"destiny_api.py failed:\n{proc.stderr}")

    # Read the freshly written JSON
    try:
        with open(WEAPONS_JSON, "r") as f:
            data = json.load(f)
            # Return the data directly - FastMCP will handle serialization
            return {"weapons": data}  # or just return data directly
    except Exception as e:
        raise RuntimeError(f"weapons_output.json missing or corrupt: {e}") from e


if __name__ == "__main__":
    async def start_all():
        websocket_task = asyncio.create_task(start_websocket_server())
        mcp.run()
        await websocket_task  # Keeps the websocket server running

    try:
        asyncio.run(start_all())
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")

