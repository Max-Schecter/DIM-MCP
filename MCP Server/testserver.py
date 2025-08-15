#!/usr/bin/env python3
"""
New test server following MCP server pattern.
Launches websocket server and waits for user input to trigger pong requests.
"""

import asyncio
import contextlib
import json
import os
from pathlib import Path

from websocket_server import request_inventory, start_websocket_server


async def handle_user_input():
    """Handle user input in a separate task"""
    print("\n🎮 Test Server Ready!")
    print("Press Enter to request inventory from DIM and save to desktop...")
    print("Type 'quit' and press Enter to exit\n")
    
    while True:
        try:
            # Use a thread executor to handle blocking input
            loop = asyncio.get_event_loop()
            user_input = await loop.run_in_executor(None, input, ">>> ")
            
            if user_input.strip().lower() == 'quit':
                print("👋 Exiting...")
                break
            
            # Any other input (including Enter) triggers inventory request
            print("📡 Requesting inventory from DIM...")
            
            try:
                response = await request_inventory()
                
                # Save response to desktop
                output_path = Path.home() / "Desktop" / "dim_inventory_response.json"
                with open(output_path, "w") as f:
                    json.dump(response, f, indent=2)
                
                # Log summary
                weapons = response.get('weapons', {}).get('data', [])
                armor = response.get('armor', {}).get('data', [])
                stores = response.get('stores', {}).get('data', [])
                
                print(f"✅ Inventory saved to: {output_path}")
                print(f"📊 Summary: {len(weapons)} weapons, {len(armor)} armor, {len(stores)} stores")
                
                # Show store info
                if stores:
                    print("🏪 Stores found:")
                    for store in stores:
                        if store.get('isVault'):
                            print(f"   🏛️ {store.get('name')} (ID: {store.get('id')})")
                        else:
                            print(f"   👤 {store.get('name')} - {store.get('className')} (Power: {store.get('powerLevel')})")
                
                print("\nPress Enter again to request inventory, or 'quit' to exit...")
                
            except Exception as e:
                print(f"❌ Failed to request inventory: {e}")
                print("Make sure DIM is running and connected...")
                
        except Exception as e:
            print(f"❌ Input error: {e}")
            break


async def main():
    """Main function following MCP server pattern"""
    print("🚀 Starting DIM Test Server...")
    print(f"🔧 Working directory: {__file__}")
    
    websocket_task = None
    input_task = None
    
    try:
        print("📡 Starting websocket server...")
        websocket_task = asyncio.create_task(start_websocket_server(), name="websocket-server")
        
        print("⌨️ Starting input handler...")
        input_task = asyncio.create_task(handle_user_input(), name="input-handler")
        
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
        print("⚡ Running websocket server and input handler concurrently...")
        await asyncio.gather(websocket_task, input_task, return_exceptions=True)
        
    except KeyboardInterrupt:
        print("\n⚠️ Keyboard interrupt received, shutting down...")
    except Exception as e:
        print(f"❌ Error running server: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cancel both tasks if one fails or we're shutting down
        print("🛑 Shutting down...")
        
        if websocket_task and not websocket_task.done():
            websocket_task.cancel()
        if input_task and not input_task.done():
            input_task.cancel()
        
        # Wait for tasks to cleanup gracefully
        if websocket_task:
            with contextlib.suppress(asyncio.CancelledError):
                await websocket_task
        if input_task:
            with contextlib.suppress(asyncio.CancelledError):
                await input_task


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")