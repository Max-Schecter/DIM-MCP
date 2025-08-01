import asyncio
import json
import logging
import ssl
from pathlib import Path
from typing import Optional

import websockets
from fastmcp import FastMCP

# MCP server setup
mcp = FastMCP("Destiny MCP Server")

# WebSocket configuration
PORT = 9130
_current_ws: Optional[websockets.WebSocketServerProtocol] = None
_weapons_event = asyncio.Event()
_armor_event = asyncio.Event()
_weapons_data = None
_armor_data = None

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


async def handle_client(websocket: websockets.WebSocketServerProtocol) -> None:
    """Handle a DIM WebSocket client connection."""
    global _current_ws, _weapons_data, _armor_data
    logger.info(f"✅ DIM connected from: {websocket.remote_address}")
    _current_ws = websocket
    try:
        async for message in websocket:
            try:
                msg = json.loads(message)
            except json.JSONDecodeError:
                if message == "ping":
                    # ignore simple pings
                    continue
                logger.info(f"📝 Received non-JSON message: {message}")
                continue

            if not isinstance(msg, dict):
                continue
            mtype = msg.get("type")
            if mtype == "hello":
                logger.info("👋 Client said hello")
            elif mtype == "weapons":
                _weapons_data = msg.get("data")
                _weapons_event.set()
                logger.info("🗃️ Weapons summary received")
            elif mtype == "armor":
                _armor_data = msg.get("data")
                _armor_event.set()
                logger.info("🦺 Armor summary received")
            elif mtype == "pong":
                logger.info("🔁 Received pong from client")
    except websockets.exceptions.ConnectionClosed as e:
        logger.info(
            f"❌ DIM disconnected (code={getattr(e, 'code', '?')}, reason={getattr(e, 'reason', '')})"
        )
    finally:
        if _current_ws is websocket:
            _current_ws = None


async def websocket_server() -> None:
    """Start the WebSocket server and run forever."""
    ssl_context = None
    cert_path = Path(__file__).with_name("cert.pem")
    key_path = Path(__file__).with_name("key.pem")
    if cert_path.exists() and key_path.exists():
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.check_hostname = False
        ssl_context.load_cert_chain(cert_path, key_path)
        logger.info("🔒 Using SSL certificates")

    logger.info(
        f"🚀 WebSocket server started on {'wss' if ssl_context else 'ws'}://localhost:{PORT}"
    )
    logger.info("Waiting for DIM to connect...\n")

    async with websockets.serve(
        handle_client,
        "localhost",
        PORT,
        ssl=ssl_context,
        ping_interval=None,
        close_timeout=10,
        max_size=None,
        max_queue=64,
    ):
        await asyncio.Future()  # run forever


async def retrieve_items() -> dict:
    """Ping the DIM client and return the latest weapons and armor JSON."""
    if _current_ws is None:
        raise RuntimeError("DIM WebSocket not connected")
    _weapons_event.clear()
    _armor_event.clear()
    await _current_ws.send("ping")
    try:
        await asyncio.wait_for(
            asyncio.gather(_weapons_event.wait(), _armor_event.wait()), timeout=10
        )
    except asyncio.TimeoutError:
        raise RuntimeError("Timed out waiting for item data from DIM")
    return {"weapons": _weapons_data, "armor": _armor_data}


@mcp.tool
async def get_inventory() -> dict:
    """Return the latest weapons and armor from the connected DIM client."""
    return await retrieve_items()


async def main() -> None:
    await asyncio.gather(websocket_server(), mcp.run_async())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down server...")
