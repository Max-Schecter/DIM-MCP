"""MCP server exposing inventory data via FastMCP tools.

This module starts both the MCP server and the accompanying WebSocket
server when executed directly. FastMCP will automatically install the
listed dependencies before running the server.
"""

from __future__ import annotations

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
from websocket_server import request_inventory, main as start_websocket_server


# FastMCP will ensure required packages are installed before start-up.
mcp = FastMCP("Destiny Inventory Server", dependencies=["websockets"])


@mcp.tool
async def weapons_for_character(current_character: str) -> list[dict]:
    """Return all weapon items owned by the given character."""

    full_data = await request_inventory()
    return get_weapons_current_character(full_data, current_character)


@mcp.tool
async def armor_for_character(current_character: str) -> list[dict]:
    """Return all armor items owned by the given character."""

    full_data = await request_inventory()
    return get_armor_current_character(full_data, current_character)


@mcp.tool
async def weapons_all() -> list[dict]:
    """Return stripped info for all weapons."""

    full_data = await request_inventory()
    return get_weapons_all(full_data)


@mcp.tool
async def armor_all() -> list[dict]:
    """Return stripped info for all armor."""

    full_data = await request_inventory()
    return get_armor_all(full_data)


@mcp.tool
async def items_by_hashes(item_hashes: List[Union[int, str]]) -> list[dict]:
    """Return items whose ID/hash matches any provided value."""

    full_data = await request_inventory()
    return get_items_by_hash(item_hashes, full_data)


async def main() -> None:
    """Run both the WebSocket server and the MCP server."""

    websocket_task = asyncio.create_task(start_websocket_server())
    try:
        await mcp.run_async()
    finally:
        websocket_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await websocket_task


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
