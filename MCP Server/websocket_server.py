import asyncio
import websockets
import json
import logging
import ssl
from pathlib import Path

# Global state - these need to be thread-safe for MCP integration
import threading
_state_lock = threading.Lock()
response_futures = {}
_current_ws = None

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

PORT = 9130
CERT_PATH = "/Users/maxschecter/Desktop/DIM-MCP/cert.pem"
KEY_PATH = "/Users/maxschecter/Desktop/DIM-MCP/key.pem"

async def getWeaponsSummary():
    weapons_output_path = Path.home() / "Desktop" / "dim_weapons.json"
    try:
        with open(weapons_output_path, "r") as f:
            weapons = json.load(f)
        return weapons
    except Exception as e:
        logger.error(f"❌ Failed to load weapons summary: {e}")
        return []

async def getArmorSummary():
    armor_output_path = Path.home() / "Desktop" / "dim_armor.json"
    try:
        with open(armor_output_path, "r") as f:
            armor = json.load(f)
        return armor
    except Exception as e:
        logger.error(f"❌ Failed to load armor summary: {e}")
        return []

async def handle_client(websocket, response_futures):
    global _current_ws
    with _state_lock:
        _current_ws = websocket
    logger.info(f"✅ DIM connected from: {websocket.remote_address}")
    try:
        async for message in websocket:
            try:
                msg = json.loads(message)
            except json.JSONDecodeError:
                logger.info(f"📝 Received non-JSON message: {message}")
                continue

            if not isinstance(msg, dict):
                continue

            mtype = msg.get("type")

            if mtype == "hello":
                logger.info("👋 Client said hello")
                continue

            if mtype == "weapons":
                weapons = msg.get("data")
                weapons_output_path = Path.home() / "Desktop" / "dim_weapons.json"
                with open(weapons_output_path, "w") as f:
                    json.dump(weapons, f, indent=2)
                logger.info(f"📁 Saved weapons summary to: {weapons_output_path}")
                logger.info("🗃️ Weapons summary received")
                continue

            if mtype == "armor":
                armor = msg.get("data")
                armor_output_path = Path.home() / "Desktop" / "dim_armor.json"
                with open(armor_output_path, "w") as f:
                    json.dump(armor, f, indent=2)
                logger.info(f"📁 Saved armor summary to: {armor_output_path}")
                logger.info("🦺 Armor summary received")
                continue

            if mtype == "pong":
                logger.info("🔁 Received pong from client")
                logger.info(f"📊 Pong data keys: {list(msg.keys())}")
                if "pong" in response_futures:
                    logger.info("✅ Setting pong future result")
                    response_futures["pong"].set_result(msg)
                else:
                    logger.info("⚠️ No pong future waiting")
                continue
    except websockets.exceptions.ConnectionClosed as e:
        logger.info(f"❌ DIM disconnected (code={getattr(e, 'code', '?')}, reason={getattr(e, 'reason', '')})")
    except Exception as e:
        logger.error(f"🚨 WebSocket error: {e}")

async def start_websocket_server():
    """Start the WebSocket server and return the server coroutine."""
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        ssl_context.load_cert_chain(CERT_PATH, KEY_PATH)
        logger.info("🔒 Using SSL certificates from DIM")
    except FileNotFoundError:
        logger.error("❌ SSL certificates not found. Run DIM to generate them.")
        raise
    except Exception as e:
        logger.error(f"❌ SSL setup error: {e}")
        raise

    logger.info(f"🚀 Secure WebSocket server started on wss://localhost:{PORT}")
    logger.info("Waiting for DIM to connect...\n")

    try:
        server = await websockets.serve(
            lambda ws: handle_client(ws, response_futures),
            "localhost",
            PORT,
            ssl=ssl_context,
            ping_interval=None,  # disable protocol pings
            close_timeout=10,
            max_size=None,       # accept messages of any size (our chunks are ~2 MB)
            max_queue=64,        # buffer more frames if needed
        )
        
        # Keep the server running
        await server.wait_closed()
    except Exception as e:
        logger.error(f"❌ Server failed to start: {e}")
        raise

async def main():
    """Main function for running the WebSocket server standalone."""
    try:
        await start_websocket_server()
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down server...")


    weapons_path = Path.home() / "Desktop" / "dim_weapons.json"
    armor_path = Path.home() / "Desktop" / "dim_armor.json"

async def request_inventory():
    with _state_lock:
        current_ws = _current_ws
        if "pong" in response_futures:
            del response_futures["pong"]
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        response_futures["pong"] = future

    if current_ws is not None:
        logger.info("📡 Sending ping to DIM")
        await current_ws.send(json.dumps({"type": "ping"}))
    else:
        raise RuntimeError("No websocket connection available")

    try:
        logger.info("⏳ Waiting for pong response...")
        response = await asyncio.wait_for(future, timeout=10.0)
        logger.info("✅ Received pong response")
        return response
    except asyncio.TimeoutError:
        logger.error("⏰ Timeout waiting for pong response")
        raise RuntimeError("Timeout waiting for inventory data")
    except Exception as e:
        logger.error(f"❌ Error waiting for pong: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down server...")