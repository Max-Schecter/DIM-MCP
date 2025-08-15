import json
import asyncio
from websocket_server import request_inventory, transfer_items, main as start_websocket_server

async def test_inventory():
    """Test inventory fetching functionality"""
    print("\n📡 Testing inventory fetch...")
    try:
        response = await request_inventory()
        
        weapons = response.get('weapons', {}).get('data', [])
        armor = response.get('armor', {}).get('data', [])
        
        print(f"✅ Inventory fetched successfully!")
        print(f"   📊 Found {len(weapons)} weapons and {len(armor)} armor pieces")
        
        # Show some sample items
        if weapons:
            sample_weapon = weapons[0]
            print(f"   🔫 Sample weapon: {sample_weapon.get('name', 'Unknown')} (ID: {sample_weapon.get('id', 'Unknown')})")
        
        if armor:
            sample_armor = armor[0]
            print(f"   🛡️ Sample armor: {sample_armor.get('name', 'Unknown')} (ID: {sample_armor.get('id', 'Unknown')})")
            
        return weapons, armor
        
    except Exception as e:
        print(f"❌ Inventory fetch failed: {e}")
        return [], []

async def test_transfer(item_ids: list, target_store: str):
    """Test item transfer functionality"""
    print(f"\n📦 Testing transfer of {len(item_ids)} items to {target_store}...")
    try:
        response = await transfer_items(item_ids, target_store)
        
        if response.get('success'):
            results = response.get('results', [])
            success_count = len([r for r in results if r.get('success')])
            fail_count = len([r for r in results if not r.get('success')])
            
            print(f"✅ Transfer completed: {success_count} successful, {fail_count} failed")
            
            # Show detailed results
            for result in results:
                status = "✅" if result.get('success') else "❌"
                item_id = result.get('instanceId', 'Unknown')
                error = result.get('error', '')
                print(f"   {status} {item_id[:16]}... {f'- {error}' if error else ''}")
        else:
            print(f"❌ Transfer failed: {response.get('error')}")
            
    except Exception as e:
        print(f"❌ Transfer test failed: {e}")

async def handle_user_input():
    """Interactive command handler"""
    print("\n🎮 Interactive Test Commands:")
    print("   'inventory' - Test inventory fetch")
    print("   'transfer' - Test item transfer (requires inventory first)")
    print("   'ping' - Original ping test")
    print("   'quit' - Exit")
    
    weapons, armor = [], []
    
    while True:
        cmd = await asyncio.get_event_loop().run_in_executor(None, input, "\n>>> ")
        cmd = cmd.strip().lower()
        
        if cmd == "quit":
            print("👋 Exiting...")
            break
            
        elif cmd == "inventory":
            weapons, armor = await test_inventory()
            
        elif cmd == "transfer":
            if not weapons and not armor:
                print("❌ No inventory data available. Run 'inventory' command first.")
                continue
                
            # Use first few items for testing
            test_items = []
            all_items = weapons + armor
            
            if len(all_items) >= 2:
                test_items = [item['id'] for item in all_items[:2]]
                print(f"🎯 Selected items for transfer:")
                for i, item in enumerate(all_items[:2]):
                    print(f"   {i+1}. {item.get('name', 'Unknown')} from {item.get('owner', 'Unknown')}")
                
                # Ask for target
                target = await asyncio.get_event_loop().run_in_executor(None, input, "Enter target (vault/character name): ")
                await test_transfer(test_items, target.strip())
            else:
                print("❌ Need at least 2 items in inventory for transfer test")
                
        elif cmd == "ping":
            # Original ping functionality
            try:
                print("[DEBUG] Calling request_inventory...")
                response = await request_inventory()
                pretty_response = json.dumps(response, indent=2)
                print("[DEBUG] Inventory response (pretty):")
                print(pretty_response)
            except Exception as e:
                print(f"[ERROR] Failed to request inventory: {e}")
                
        else:
            print("❌ Unknown command. Try 'inventory', 'transfer', 'ping', or 'quit'")




if __name__ == "__main__":
    async def start_all():
        server_task = asyncio.create_task(start_websocket_server())
        input_task = asyncio.create_task(handle_user_input())
        await asyncio.gather(server_task, input_task)

    try:
        asyncio.run(start_all())
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
