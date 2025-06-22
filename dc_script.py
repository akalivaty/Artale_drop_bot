import json
import os

import discord
from discord.ext import commands

from py_drops import create_item_to_monster_map

TOKEN = os.getenv("DISCORD_TOKEN")

# 檢查 TOKEN 是否存在
if not TOKEN:
    raise ValueError("在 .env 檔案中找不到 DISCORD_TOKEN")

# --- 新增：啟動時載入通用別名 ---
GENERAL_ALIASES = {}
try:
    with open("general_alias.json", "r", encoding="utf-8") as f:
        GENERAL_ALIASES = json.load(f)
    print("成功載入 general_alias.json。")
except FileNotFoundError:
    print("未找到 general_alias.json，將不使用通用別名功能。")
except json.JSONDecodeError:
    print("警告：general_alias.json 格式錯誤，將不使用通用別名功能。")

# 設定 Bot 的指令前綴和必要的 intents
# intents 是必要的，以確保您的機器人可以讀取訊息內容
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


def search_drops(item_query: str) -> str:
    item_to_monsters = create_item_to_monster_map()
    keywords = item_query.split()

    found_results = {}

    for item_name, data in item_to_monsters.items():
        if all(key in item_name for key in keywords):
            if "real_name" in data:
                real_name = data["real_name"]
                if (
                    real_name in item_to_monsters
                    and "monsters" in item_to_monsters[real_name]
                ):
                    monsters = item_to_monsters[real_name]["monsters"]
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
    # output_lines.append("")  # 空一行

    sorted_items = sorted(
        found_results.items(), key=lambda item: item[1]["matched_name"]
    )

    for real_name, result_data in sorted_items:
        monsters = result_data["monsters"]
        matched_name = result_data["matched_name"]

        display_name = (
            f"{matched_name} ({real_name})" if real_name != matched_name else real_name
        )

        output_lines.append("-" * 50)
        output_lines.append(f"掉落物:【**{display_name}**】")
        for monster in sorted(monsters):
            output_lines.append(f"- {monster}")

    final_message = "\n".join(output_lines)

    # Discord 訊息長度限制為 2000 字元
    if len(final_message) > 1990:  # 預留空間給 code block
        return "結果太多，無法在單一訊息中顯示。請嘗試更精確的關鍵字。"

    return final_message


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


# 執行 Bot
bot.run(TOKEN)
