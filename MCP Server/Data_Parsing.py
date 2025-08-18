import json

#with open("dim_inventory_response.json", "r") as f:
  # full_data = json.load(f)

def get_weapons_current_character(full_data, current_character):
    weapons_data = full_data.get("weapons", {}).get("data", [])
    filtered_weapons = [w for w in weapons_data if w.get("owner") == current_character]
    return json.dumps(filtered_weapons, indent=2)

def get_armor_current_character(full_data, current_character):
    armor_data = full_data.get("armor", {}).get("data", [])
    filtered_armor = [w for w in armor_data if w.get("owner") == current_character]
    return json.dumps(filtered_armor, indent=2)

def get_weapons_all(full_data):
    weapons_data = full_data.get("weapons", {}).get("data", [])
    stripped_weapons = [{"id": w.get("id"), "name": w.get("name"), "owner": w.get("owner"), "gear_tier": w.get("gearTier"), "type": w.get("type"), "element": w.get("element")} for w in weapons_data]
    return json.dumps(stripped_weapons, indent=2)

def get_armor_all(full_data):
    armor_data = full_data.get("armor", {}).get("data", [])
    stripped_armor = [{"id": w.get("id"), "name": w.get("name"), "owner": w.get("owner"), "gear_tier": w.get("gearTier"), "type": w.get("type"), "stat_total": w.get("stats", {}).get("Total")} for w in armor_data]
    return json.dumps(stripped_armor, indent=2)

def get_most_recent_character_id(full_data):
    stores = full_data["stores"]["data"]
    characters = [s for s in stores if not s["isVault"]]
    return max(characters, key=lambda c: c["lastPlayed"])["id"]

def get_most_recent_character_name(full_data):
    stores = full_data["stores"]["data"]
    characters = [s for s in stores if not s["isVault"]]
    return max(characters, key=lambda c: c["lastPlayed"])["name"]


def get_items_by_hash(item_hashes, full_data):
    """
    item_hashes: list of item hash strings or integers
    full_data: loaded JSON object from dim_inventory_response.json
    """
    gear = full_data.get("weapons", {}).get("data", [])
    item_hashes_str = set(str(h) for h in item_hashes)
    matched_items = [item for item in gear if str(item.get("id")) in item_hashes_str]
    return json.dumps(matched_items, indent=2)

def process_transfer_response(response):
    """
    Process transfer response and return a friendly string message.
    
    Args:
        response: Transfer response dict from websocket server
        
    Returns:
        str: Friendly message describing transfer results
    """
    if response.get("success"):
        results = response.get("results", [])
        success_count = len([r for r in results if r.get("success")])
        fail_count = len([r for r in results if not r.get("success")])
        
        if fail_count == 0:
            return f"Successfully transferred {success_count} items to your character."
        else:
            failed_items = [r.get("instanceId") for r in results if not r.get("success")]
            return f"Transferred {success_count} items successfully. Failed to transfer {fail_count} items: {', '.join(failed_items[:3])}{'...' if len(failed_items) > 3 else ''}"
    else:
        error_msg = response.get("error", "Unknown error")
        return f"Transfer failed: {error_msg}"


#function_output = get_armor_current_character(full_data, "Human Warlock")




#item_hashes = [
#  "6917530125735572654",
#  "6917530126853337644",
#  "6917529265231429541",
#  "6917530125735572654"
#]



#function_output = get_most_recent_character(full_data)
#with open("test.json", "w") as f:
  #  json.dump(function_output, f, indent=2)


