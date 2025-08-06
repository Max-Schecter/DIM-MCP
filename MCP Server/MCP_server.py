from fastmcp import FastMCP
from typing import List, Union
import subprocess, json, os, sys
import asyncio
from websocket_server import request_inventory, main as start_websocket_server
from Data_Parsing import (
    get_weapons_current_character,
    get_armor_current_character,
    get_weapons_all,
    get_armor_all,
    get_items_by_hash,
)

if __name__ == "__main__":
    # Create the MCP server object
    mcp = FastMCP("Destiny Inventory Server")

    @mcp.tool
    def weapons_for_character(current_character: str) -> list[dict]:
        """Return all weapon items owned by the given character. Input: current_character (e.g., 'Human Warlock'). Output: list of weapon dicts."""
        full_data = request_inventory()
        result = get_weapons_current_character(full_data, current_character)
        return result

    @mcp.tool
    def armor_for_character(current_character: str) -> list[dict]:
        """Return all armor items owned by the given character. Input: current_character. Output: list of armor dicts."""
        full_data = request_inventory()
        result = get_armor_current_character(full_data, current_character)
        return result

    @mcp.tool
    def weapons_all() -> list[dict]:
        """Return stripped info for all weapons. Output: list of weapon dicts with id/name/owner/gear_tier/type/element."""
        full_data = request_inventory()
        result = get_weapons_all(full_data)
        return result

    @mcp.tool
    def armor_all() -> list[dict]:
        """Return stripped info for all armor. Output: list of armor dicts with id/name/owner/gear_tier/type/stat_total."""
        full_data = request_inventory()
        result = get_armor_all(full_data)
        return result

    @mcp.tool
    def items_by_hashes(item_hashes: List[Union[int, str]]) -> list[dict]:
        """Return items whose id/hash matches any provided value. Input: item_hashes (ints/strings). Output: list of matching item dicts."""
        full_data = request_inventory()
        result = get_items_by_hash(item_hashes, full_data)
        return result

    # Start the websocket server in the background
    async def start_websocket_background():
        await start_websocket_server()

    # Create and start the websocket server task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    websocket_task = loop.create_task(start_websocket_background())

    try:
        # Run the MCP server (this blocks)
        mcp.run()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        websocket_task.cancel()
        loop.close()