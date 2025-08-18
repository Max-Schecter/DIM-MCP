from __future__ import annotations

"""MCP server exposing inventory data via FastMCP tools.

This module starts both the MCP server and the accompanying WebSocket
server when executed directly. FastMCP will automatically install the
listed dependencies before running the server.
"""

import asyncio
import contextlib
import os
from typing import List, Union

from fastmcp import FastMCP

from Data_Parsing import (
    get_armor_all,
    get_armor_current_character,
    get_items_by_hash,
    get_weapons_all,
    get_weapons_current_character,
    get_most_recent_character_id,
    get_most_recent_character_name,
    process_transfer_response,

)
from websocket_server import request_inventory, transfer_items, start_websocket_server


# FastMCP will ensure required packages are installed before start-up.
mcp = FastMCP("Destiny_Inventory_Server", dependencies=["websockets"])


@mcp.tool
async def weapons_for_current_character() -> str:
    """Return all weapon items owned by the current character, only use if user is requesting armor for current character. Otherwise default to account wide."""

    full_data = await request_inventory()
    return get_weapons_current_character(full_data, "Human Warlock")

@mcp.tool
async def get_important_destiny_rules() -> str:
    """
    Returns important information about Destiny 2 loadouts. No input required. Safe to cache for the session.
    """
    return (
        "### Important Destiny 2 Loadout Rules\n"
        "- Only **ONE exotic weapon** can be equipped\n"
        "- Only **ONE exotic armor piece** can be equipped"
    )

@mcp.tool
async def armor_for_current_character()-> str:
    """Return all armor items owned by the current character, only use if user is requesting armor for current character. Otherwise default to account wide."""

    full_data = await request_inventory()
    return get_armor_current_character(full_data, "Human Warlock")


@mcp.tool
async def get_weapons_account_wide() -> str:
    """Return stripped info for all weapons on account (including vault)."""

    full_data = await request_inventory()
    return get_weapons_all(full_data)


@mcp.tool
async def get_armor_account_wide() -> str:
    """Return stripped info for all armor on account (including vault)."""

    full_data = await request_inventory()
    return get_armor_all(full_data)

@mcp.tool
async def items_by_hashes(item_hashes: List[Union[int, str]]) -> str:
    """Return items whose ID/hash matches any provided value."""

    full_data = await request_inventory()
    return get_items_by_hash(item_hashes, full_data)

@mcp.tool
async def transfer_items_to_character(item_hashes: List[Union[int, str]]) -> str:
    """Transfer items whose ID/hash matches any provided value to the user's current character."""
    full_data = await request_inventory()
    character_id = get_most_recent_character_id(full_data)

    response = await transfer_items(item_hashes, character_id)
    return process_transfer_response(response)

@mcp.tool
async def transfer_items_to_vault(item_hashes: List[Union[int, str]]) -> str:
    """Transfer items whose ID/hash matches any provided value to the user's vault."""

    response = await transfer_items(item_hashes, "vault")
    return process_transfer_response(response)

@mcp.tool
async def get_current_character() -> str:
    """Return the race and class of the user's current character."""
    full_data = await request_inventory()

    return get_most_recent_character_name(full_data)

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

        # --- Orphan guard: exit if launcher disappears (PPID becomes 1) ---
        async def _orphan_guard():
            while True:
                try:
                    if os.getppid() == 1:
                        # Fast, reliable exit to avoid zombies or relaunch loops
                        os._exit(0)
                    await asyncio.sleep(2)
                except Exception:
                    # If anything goes wrong, fail safe by exiting
                    os._exit(0)
        asyncio.create_task(_orphan_guard(), name="orphan-guard")
        # -----------------------------------------------------------------

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
