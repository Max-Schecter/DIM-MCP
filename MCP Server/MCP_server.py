from __future__ import annotations

"""MCP server exposing inventory data via FastMCP tools.

This module starts both the MCP server and the accompanying WebSocket
server when executed directly. FastMCP will automatically install the
listed dependencies before running the server.
"""

import asyncio
import contextlib
import os
import subprocess
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


async def start_dim_process():
    """Start the DIM development server using pnpm start."""
    print("🎮 Starting DIM with pnpm start...")
    
    # Get the parent directory (DIM-MCP root)
    dim_root = os.path.dirname(os.path.dirname(__file__))
    
    try:
        # Start pnpm start process
        process = await asyncio.create_subprocess_exec(
            'pnpm', 'start',
            cwd=dim_root,
            stdout=subprocess.DEVNULL,  # Suppress DIM output
            stderr=subprocess.DEVNULL   # Suppress DIM errors
        )
        
        print(f"✅ DIM process started with PID: {process.pid}")
        print("   DIM will be available at: https://localhost:8080")
        
        return process
        
    except Exception as e:
        print(f"❌ Failed to start DIM: {e}")
        return None


async def stop_dim_process(dim_process):
    """Stop the DIM process gracefully."""
    if dim_process and dim_process.returncode is None:
        print("🛑 Stopping DIM process...")
        try:
            # Send SIGTERM for graceful shutdown
            dim_process.terminate()
            
            # Wait up to 10 seconds for graceful shutdown
            try:
                await asyncio.wait_for(dim_process.wait(), timeout=10.0)
                print("✅ DIM process stopped gracefully")
            except asyncio.TimeoutError:
                print("⚠️ DIM process didn't stop gracefully, forcing kill...")
                dim_process.kill()
                await dim_process.wait()
                print("✅ DIM process forcefully killed")
                
        except Exception as e:
            print(f"❌ Error stopping DIM process: {e}")


async def main() -> None:
    """Run the WebSocket server, MCP server, and DIM development server."""
    
    print("🚀 Starting DIM MCP Server...")
    print(f"🔧 Working directory: {os.path.dirname(__file__)}")
    
    websocket_task = None
    mcp_task = None
    dim_process = None
    
    try:
        # Check if pnpm is available
        try:
            result = await asyncio.create_subprocess_exec(
                'pnpm', '--version',
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            await result.wait()
            if result.returncode != 0:
                raise Exception("pnpm not found")
        except Exception:
            print("❌ pnpm is not available - DIM will not start automatically")
            
        # Start DIM first (only if pnpm is available)  
        if 'result' in locals() and result.returncode == 0:
            print("📦 Starting DIM development server...")
            dim_process = await start_dim_process()
            if not dim_process:
                print("❌ Failed to start DIM, continuing without it...")
        else:
            print("⚠️ Skipping DIM startup - pnpm not available")
        
        print("📡 Starting websocket server...")
        websocket_task = asyncio.create_task(start_websocket_server(), name="websocket-server")
        
        print("🤖 Starting MCP server...")
        mcp_task = asyncio.create_task(mcp.run_async(), name="mcp-server")
        
        # Run both server tasks concurrently
        print("⚡ All services started:")
        if dim_process:
            print("   ✅ DIM: https://localhost:8080")
        print("   ✅ WebSocket: ws://localhost:8765")
        print("   ✅ MCP: stdio")
        
        await asyncio.gather(websocket_task, mcp_task, return_exceptions=True)
        
    except KeyboardInterrupt:
        print("\n⚠️ Keyboard interrupt received, shutting down...")
    except Exception as e:
        print(f"❌ Error running servers: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Shutdown sequence
        print("\n🛑 Shutting down all services...")
        
        # Cancel server tasks first
        if websocket_task and not websocket_task.done():
            print("   Stopping websocket server...")
            websocket_task.cancel()
        if mcp_task and not mcp_task.done():
            print("   Stopping MCP server...")
            mcp_task.cancel()
        
        # Wait for server tasks to cleanup gracefully
        if websocket_task:
            with contextlib.suppress(asyncio.CancelledError):
                await websocket_task
        if mcp_task:
            with contextlib.suppress(asyncio.CancelledError):
                await mcp_task
        
        # Stop DIM process last
        if dim_process:
            print("   Stopping DIM...")
            await stop_dim_process(dim_process)
        
        print("✅ All services stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
