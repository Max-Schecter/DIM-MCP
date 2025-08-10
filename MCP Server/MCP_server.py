from __future__ import annotations

"""MCP server exposing inventory data via FastMCP tools.

This module starts both the MCP server and the accompanying WebSocket
server when executed directly. FastMCP will automatically install the
listed dependencies before running the server.
"""

import asyncio
import contextlib
from typing import List, Union

from fastmcp import FastMCP

from Data_Parsing import (
    get_armor_all,
    get_armor_current_character,
    get_items_by_hash,
    get_weapons_all,
    get_weapons_current_character,
)
from websocket_server import request_inventory, start_websocket_server


# FastMCP will ensure required packages are installed before start-up.
mcp = FastMCP("Destiny Inventory Server", dependencies=["websockets"])


@mcp.tool
async def weapons_for_character() -> str:
    """Return all weapon items owned by the given character."""

    full_data = await request_inventory()
    return get_weapons_current_character(full_data, "Human Warlock")


@mcp.tool
async def armor_for_character()-> str:
    """Return all armor items owned by the given character."""

    full_data = await request_inventory()
    return get_armor_current_character(full_data, "Human Warlock")


@mcp.tool
async def weapons_all() -> str:
    """Return stripped info for all weapons."""

    full_data = await request_inventory()
    return get_weapons_all(full_data)


@mcp.tool
async def armor_all() -> str:
    """Return stripped info for all armor."""

    full_data = await request_inventory()
    return get_armor_all(full_data)


@mcp.tool
async def items_by_hashes(item_hashes: List[Union[int, str]]) -> str:
    """Return items whose ID/hash matches any provided value."""

    full_data = await request_inventory()
    return get_items_by_hash(item_hashes, full_data)


async def main() -> None:
    """Run both the WebSocket server and the MCP server."""
    
    print("🚀 Starting DIM MCP Server...")
    print(f"🔧 Working directory: {__file__}")
    
    websocket_task = None
    mcp_task = None
    
    try:
        print("📡 Starting websocket server...")
        websocket_task = asyncio.create_task(start_websocket_server(), name="websocket-server")
        
        print("🤖 Starting MCP server...")
        mcp_task = asyncio.create_task(mcp.run_async(), name="mcp-server")
        
        # Run both tasks concurrently
        print("⚡ Running both servers concurrently...")
        await asyncio.gather(websocket_task, mcp_task, return_exceptions=True)
        
    except KeyboardInterrupt:
        print("\n⚠️ Keyboard interrupt received, shutting down...")
    except Exception as e:
        print(f"❌ Error running servers: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cancel both tasks if one fails or we're shutting down
        print("🛑 Shutting down servers...")
        
        if websocket_task and not websocket_task.done():
            websocket_task.cancel()
        if mcp_task and not mcp_task.done():
            mcp_task.cancel()
        
        # Wait for tasks to cleanup gracefully
        if websocket_task:
            with contextlib.suppress(asyncio.CancelledError):
                await websocket_task
        if mcp_task:
            with contextlib.suppress(asyncio.CancelledError):
                await mcp_task


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
