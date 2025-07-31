import asyncio
import websockets
import json
import logging
import ssl
from pathlib import Path

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

PORT = 9130
CERT_PATH = "/Users/maxschecter/Desktop/DIM-MCP/cert.pem"
KEY_PATH = "/Users/maxschecter/Desktop/DIM-MCP/key.pem"

async def handle_client(websocket):
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
                continue
    except websockets.exceptions.ConnectionClosed as e:
        logger.info(f"❌ DIM disconnected (code={getattr(e, 'code', '?')}, reason={getattr(e, 'reason', '')})")
    except Exception as e:
        logger.error(f"🚨 WebSocket error: {e}")

async def main():
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        ssl_context.load_cert_chain(CERT_PATH, KEY_PATH)
        logger.info("🔒 Using SSL certificates from DIM")
    except FileNotFoundError:
        logger.error("❌ SSL certificates not found. Run DIM to generate them.")
        return
    except Exception as e:
        logger.error(f"❌ SSL setup error: {e}")
        return

    logger.info(f"🚀 Secure WebSocket server started on wss://localhost:{PORT}")
    logger.info("Waiting for DIM to connect...\n")

    try:
        async with websockets.serve(
            handle_client,
            "localhost",
            PORT,
            ssl=ssl_context,
            ping_interval=None,  # disable protocol pings
            close_timeout=10,
            max_size=None,       # accept messages of any size (our chunks are ~2 MB)
            max_queue=64,        # buffer more frames if needed
        ):
            await asyncio.Future()  # Run forever
    except Exception as e:
        logger.error(f"❌ Server failed to start: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down server...")