import discord
from discord.ext import commands
import os
from py_drops import create_item_to_monster_map

TOKEN = os.getenv("DISCORD_TOKEN")

# 檢查 TOKEN 是否存在
if not TOKEN:
    raise ValueError("在 .env 檔案中找不到 DISCORD_TOKEN")

# 設定 Bot 的指令前綴和必要的 intents
# intents 是必要的，以確保您的機器人可以讀取訊息內容
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    """當 Bot 成功連線到 Discord 時執行的事件"""
    print(f"Bot 已成功登入為 {bot.user}")
    print("-------------------")


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
    display_keywords = "' 和 '".join(keywords)
    output_lines.append(f"===== 找到同時含有「{display_keywords}」的掉落物結果 =====")
    output_lines.append("")  # 空一行

    sorted_items = sorted(
        found_results.items(), key=lambda item: item[1]["matched_name"]
    )

    for real_name, result_data in sorted_items:
        monsters = result_data["monsters"]
        matched_name = result_data["matched_name"]

        display_name = (
            f"{matched_name} ({real_name})" if real_name != matched_name else real_name
        )

        output_lines.append(f"掉落物: {display_name}")
        for monster in sorted(monsters):
            output_lines.append(f"  - {monster}")
        output_lines.append("-" * 30)

    final_message = "\n".join(output_lines)

    # Discord 訊息長度限制為 2000 字元
    if len(final_message) > 1990:  # 預留空間給 code block
        return "結果太多，無法在單一訊息中顯示。請嘗試更精確的關鍵字。"

    return final_message


@bot.command(name="drop")
async def search_drops_command(ctx, *, item_query: str):
    """
    一個 Discord 指令，當使用者輸入 !drop <物品名稱> 時觸發。
    """
    try:
        # 顯示 "正在處理中" 的訊息
        processing_message = await ctx.send(f"正在查詢【{item_query}】...")

        # 呼叫您的腳本邏輯，它現在會回傳一個格式化好的字串
        output = search_drops(item_query)

        # 編輯訊息以顯示最終結果，使用 code block 格式化以保持排版
        await processing_message.edit(content=f"```\n{output}\n```")

    except Exception as e:
        # 如果發生錯誤，發送錯誤訊息
        await ctx.send(f"執行時發生錯誤：{e}")
        print(f"執行指令時發生錯誤: {e}")


@search_drops_command.error
async def search_drops_command_error(ctx, error):
    """處理 !drop 指令的特定錯誤"""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("請輸入要查詢的物品名稱。用法: `!drop <物品名稱>`")
    else:
        await ctx.send("指令發生未預期的錯誤，請聯繫管理員。")
        print(f"指令 '{ctx.command}' 發生錯誤: {error}")


# 執行 Bot
bot.run(TOKEN)
