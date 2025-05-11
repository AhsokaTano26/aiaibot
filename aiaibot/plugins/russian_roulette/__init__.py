from nonebot import get_plugin_config
from nonebot import on_command
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    Message,
    MessageSegment
)
from nonebot.params import CommandArg
import random
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="Russian_roulette",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)


# 创建命令处理器
set_roulette = on_command("轮盘赌", priority=10)
fire = on_command("开火", priority=10)

# 存储游戏状态：{(群号, 用户ID): 子弹数量}
roulette_games = {}


@set_roulette.handle()
async def handle_set_roulette(event: GroupMessageEvent, args: Message = CommandArg()):
    """处理设置子弹数量"""
    arg = args.extract_plain_text().strip()

    if not arg.isdigit():
        await set_roulette.finish("⚠️ 请输入1-5之间的整数作为子弹数量！")
        return

    bullet_num = int(arg)
    if not (1 <= bullet_num <= 5):
        await set_roulette.finish("⚠️ 子弹数量必须在1到5之间！")
        return

    # 存储游戏状态
    game_key = (event.group_id, event.user_id)
    roulette_games[game_key] = bullet_num
    await set_roulette.finish(f"🔫 已装入 {bullet_num} 发子弹，发送【/开火】进行射击！")


@fire.handle()
async def handle_fire(event: GroupMessageEvent, bot: Bot):
    """处理开火命令"""
    game_key = (event.group_id, event.user_id)

    if game_key not in roulette_games:
        await fire.finish("⚠️ 请先使用【/轮盘赌 数字】装入子弹！")
        return

    bullet_num = roulette_games.pop(game_key)
    rand = random.randint(50, 300)

    if rand <= bullet_num*50:
        try:
            # 禁言5分钟（300秒）
            await bot.set_group_ban(
                group_id=event.group_id,
                user_id=event.user_id,
                duration=60
            )
            await fire.send(MessageSegment.at(event.user_id) + "💥 砰！很不幸，你中弹了！（已被禁言1分钟）")
        except Exception as e:
            await fire.send(f"⚠️ 禁言失败：{str(e)}")
    else:
        await fire.send(MessageSegment.at(event.user_id) + "🔰 咔嗒～ 运气不错，这次是空枪！")