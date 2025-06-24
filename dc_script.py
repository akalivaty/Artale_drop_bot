import json
import os

import discord
from discord.ext import commands

from py_drops import create_item_to_monster_map
import unicodedata

TOKEN = os.getenv("DISCORD_TOKEN")

# 檢查 TOKEN 是否存在
if not TOKEN:
    raise ValueError("在 .env 檔案中找不到 DISCORD_TOKEN")

# --- 新增：啟動時載入通用別名 ---
MOSTER_DROP_DATA = {}
ITEM_TO_MONSTER = {}
GENERAL_ALIASES = {}
try:
    # 怪物掉落資訊
    if os.path.exists("drop_data.json"):
        try:
            with open("drop_data.json", "r", encoding="utf-8") as f:
                print("成功從 drop_data.json 載入資料。")
                MOSTER_DROP_DATA = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"讀取快取檔案時發生錯誤 ({e})，將重新建立。")

    # 掉落物 to 怪物
    ITEM_TO_MONSTER = create_item_to_monster_map()

    # 掉落物通用別名
    with open("general_alias.json", "r", encoding="utf-8") as f:
        GENERAL_ALIASES = json.load(f)
    print("成功載入 general_alias.json。")
except FileNotFoundError:
    print("未找到 general_alias.json，將不使用通用別名功能。")
except json.JSONDecodeError:
    print("警告：general_alias.json 格式錯誤，將不使用通用別名功能。")

# 設定 Bot 的指令前綴和必要的 intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)


@bot.event
async def on_ready():
    """當 Bot 成功連線到 Discord 時執行的事件"""
    try:
        synced = await bot.tree.sync()
        print(f"成功同步 {len(synced)} 個指令")
    except Exception as e:
        print(f"同步指令時發生錯誤: {e}")

    print(f"Bot 已成功登入為 {bot.user}")
    print("-------------------")


def apply_general_aliases(query: str) -> str:
    """
    將使用者輸入的查詢根據 GENERAL_ALIASES 字典進行關鍵字替換。
    """
    processed_query = query
    for real_keyword, alias in GENERAL_ALIASES.items():
        if alias in processed_query:
            processed_query = processed_query.replace(alias, real_keyword)
    return processed_query


def get_display_width(text):
    """計算字串的實際顯示寬度（中日韓全形算2，半形算1）"""
    width = 0
    for ch in text:
        if unicodedata.east_asian_width(ch) in ("F", "W", "A"):
            width += 2
        else:
            width += 1
    return width


def pad_to_width(text, total_width=30):
    """將字串補空格到指定寬度"""
    pad_len = total_width - get_display_width(text)
    return text + " " * max(0, pad_len)


def calc_tab_count(left: str, min_tabs=3, tab_width=8):
    """根據左側字串長度自動決定需要幾個 tab 才能對齊右側"""
    width = get_display_width(left)
    # 每個 tab 約等於 tab_width 個半形字
    tabs = max(min_tabs, (tab_width * min_tabs - width) // tab_width)
    return "\t" * tabs


def search_drops(item_query: str) -> str:
    """
    根據掉落物名稱關鍵字模糊搜尋其所有掉落怪物
    """
    keywords = item_query.split()

    found_results = {}

    for item_name, data in ITEM_TO_MONSTER.items():
        if all(key in item_name for key in keywords):
            if "real_name" in data:
                real_name = data["real_name"]
                if (
                    real_name in ITEM_TO_MONSTER
                    and "monsters" in ITEM_TO_MONSTER[real_name]
                ):
                    monsters = ITEM_TO_MONSTER[real_name]["monsters"]
                    found_results[real_name] = {
                        "monsters": monsters,
                        "matched_name": item_name,
                    }
            elif "monsters" in data:
                real_name = item_name
                monsters = data["monsters"]
                if real_name not in found_results:
                    found_results[real_name] = {
                        "monsters": monsters,
                        "matched_name": real_name,
                    }

    if not found_results:
        return "找不到任何掉落物名稱中同時含有輸入的所有關鍵字。"

    # 組合回傳訊息
    output_lines = []
    display_keywords = " ".join(keywords)
    output_lines.append(f"找到含有【{display_keywords}】的掉落物結果")

    sorted_items = sorted(
        found_results.items(), key=lambda item: len(item[1]["matched_name"])
    )

    for real_name, result_data in sorted_items:
        monsters = result_data["monsters"]
        matched_name = result_data["matched_name"]

        display_name = (
            f"{matched_name} ({real_name})" if real_name != matched_name else real_name
        )

        output_lines.append(" ")
        output_lines.append("-" * 50)
        output_lines.append(" ")
        output_lines.append(f"掉落物:【{display_name}】")
        output_lines.append(" ")
        # 先計算這批 monsters 的最大寬度
        max_width = max(get_display_width(x) for x in monsters) if monsters else 0

        if monsters:
            row = []
            for idx, monster in enumerate(sorted(monsters, key=len), 1):
                row.append(monster)
                if idx % 2 == 0:
                    left = pad_to_width(row[0], max_width)
                    output_lines.append(f"{left}\t{row[1]}")
                    row = []
            if row:
                output_lines.append(row[0])
        else:
            output_lines.append("(無掉落怪物)")

    final_message = "\n".join(output_lines)

    if len(final_message) > 2000:
        return "結果太多，無法在單一訊息中顯示。請嘗試更精確的關鍵字。"

    return f"```\n{final_message}\n```"


def search_monster_drops(monster_query: str) -> str:
    """
    根據怪物名稱關鍵字模糊搜尋其所有掉落物。
    """
    found_monsters = {}
    for monster_name, items in MOSTER_DROP_DATA.items():
        if monster_query in monster_name:
            found_monsters[monster_name] = items

    if not found_monsters:
        return f"找不到任何名稱中含有【{monster_query}】的怪物。"

    output_lines = []
    output_lines.append(f"找到名稱中含有【{monster_query}】的怪物")

    for monster_name, items in sorted(found_monsters.items(), key=lambda x: len(x[0])):
        output_lines.append(" ")
        output_lines.append("-" * 50)
        output_lines.append(" ")
        output_lines.append(f"【{monster_name}】的掉落物:")
        output_lines.append(" ")
        # 先計算這批 items 的最大寬度
        max_width = max(get_display_width(x) for x in items) if items else 0

        if items:
            row = []
            for idx, item in enumerate(sorted(items, key=len), 1):
                row.append(item)
                if idx % 2 == 0:
                    left = pad_to_width(row[0], max_width)
                    output_lines.append(f"{left}\t{row[1]}")
                    row = []
            if row:
                output_lines.append(row[0])
        else:
            output_lines.append("(無掉落物)")

    final_message = "\n".join(output_lines)
    if len(final_message) > 2000:
        return "結果太多，無法在單一訊息中顯示。請嘗試更精確的關鍵字。"
    return f"```\n{final_message}\n```"


@bot.tree.command(name="drop", description="查詢物品的掉落怪物")
async def search_drops_command(interaction: discord.Interaction, item: str):
    """
    一個 Discord 斜線指令，用來查詢掉落物。
    """
    try:
        # 1. 立即回應，讓使用者知道機器人已收到指令 (避免逾時)
        await interaction.response.defer()

        # 2. 執行您的耗時邏輯
        processed_query = apply_general_aliases(item)
        output = search_drops(processed_query)

        # 3. 傳送最終結果
        await interaction.followup.send(output)

    except Exception as e:
        # 如果發生錯誤，發送錯誤訊息
        if not interaction.response.is_done():
            await interaction.response.send_message(f"執行時發生錯誤：{e}")
        else:
            await interaction.followup.send(f"執行時發生錯誤：{e}")
        print(f"執行指令時發生錯誤: {e}")


@bot.tree.command(name="mons", description="查詢指定怪物的所有掉落物")
async def search_monster_drops_command(interaction: discord.Interaction, monster: str):
    """
    一個 Discord 斜線指令，用來查詢怪物的掉落物。
    """
    try:
        # 1. 立即回應
        await interaction.response.defer()

        # 2. 執行搜尋邏輯
        output = search_monster_drops(monster)

        # 3. 傳送最終結果
        await interaction.followup.send(output)

    except Exception as e:
        # 如果發生錯誤，發送錯誤訊息
        if not interaction.response.is_done():
            await interaction.response.send_message(f"執行時發生錯誤：{e}")
        else:
            await interaction.followup.send(f"執行時發生錯誤：{e}")
        print(f"執行指令時發生錯誤: {e}")


# 執行
bot.run(TOKEN)
