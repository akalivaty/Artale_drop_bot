import json
from collections import defaultdict
import os


def create_item_to_monster_map(cache_file="item_map_cache.json"):
    """
    [優化] 檢查是否有快取檔案，若無則從 drop_data.json 和 alias.json 建立並匯出。
    快取資料結構包含真實物品與別名的關聯。
    """
    # 1. 檢查快取檔案是否存在
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                print(f"成功從快取檔案 '{cache_file}' 載入資料。")
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"讀取快取檔案時發生錯誤 ({e})，將重新建立。")

    # 2. 如果快取不存在或讀取失敗，則從原始資料建立
    print("找不到快取檔案，正在從 'drop_data.json' 和 'alias.json' 建立新的資料對應...")
    try:
        with open("drop_data.json", "r", encoding="utf-8") as f:
            drop_data = json.load(f)
    except FileNotFoundError:
        print("錯誤：找不到 drop_data.json 檔案。請確保腳本與檔案在同一個資料夾中。")
        return None
    except json.JSONDecodeError:
        print("錯誤：drop_data.json 檔案格式不正確，無法解析。")
        return None

    # 讀取別名檔案
    alias_data = {}
    try:
        with open("alias.json", "r", encoding="utf-8") as f:
            alias_data = json.load(f)
        print("成功載入 alias.json。")
    except FileNotFoundError:
        print("警告：找不到 alias.json 檔案，將不使用別名功能。")
    except json.JSONDecodeError:
        print("警告：alias.json 檔案格式不正確，無法解析，將不使用別名功能。")

    # 建立新的資料結構:
    # - 真實物品: {"monsters": [...]}
    # - 別名: {"real_name": "真實物品名稱"}
    item_map = {}

    # 步驟 A: 處理 drop_data.json，建立真實物品的掉落列表
    temp_item_map = defaultdict(list)
    for monster, items in drop_data.items():
        for item in items:
            if monster not in temp_item_map[item]:
                temp_item_map[item].append(monster)

    for item, monsters in temp_item_map.items():
        item_map[item] = {"monsters": monsters}

    # 步驟 B: 處理 alias.json，建立別名到真實名稱的連結
    # (key: 真實名稱, value: 別名)
    for real_name, alias_name in alias_data.items():
        # 只處理在掉落資料中存在的真實物品
        if real_name in item_map:
            item_map[alias_name] = {"real_name": real_name}

    # 3. 將新建的資料匯出成快取檔案
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(item_map, f, ensure_ascii=False, indent=2)
        print(f"新的掉落物資料已成功建立，並匯出至 '{cache_file}'。")
    except IOError as e:
        print(f"錯誤：無法寫入快取檔案 '{cache_file}'。錯誤訊息: {e}")

    return item_map
