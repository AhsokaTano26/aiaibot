from nonebot import get_plugin_config, require
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="Silence",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

from nonebot import on_message, get_bot
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.rule import to_me
import datetime

# 定时任务需要
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

# 创建消息处理器，监听被@的群消息
matcher = on_message(rule=to_me(), priority=10, block=True)

def is_admin(event: GroupMessageEvent) -> bool:
    """验证发送者是否为群主或管理员"""
    return event.sender.role in ["owner", "admin"]

@matcher.handle()
async def handle_unban(event: GroupMessageEvent):
    if not is_admin(event):
        await matcher.finish("⚠️ 权限不足，只有群主或管理员可以使用此命令")
    # 获取消息内容
    message = event.get_message()

    # 提取消息中的@用户（排除机器人自己）
    target_users = [
        int(seg.data["qq"])
        for seg in message
        if seg.type == "at" and seg.data.get("qq") != str(event.self_id)
    ]

    if not target_users:
        await matcher.finish("请@需要解除禁言的成员")

    target_id = target_users[0]  # 取第一个被@的用户
    group_id = event.group_id

    try:
        # 解除禁言
        await get_bot().set_group_ban(
            group_id=group_id,
            user_id=target_id,
            duration=0
        )
    except Exception as e:
        await matcher.finish(f"解除禁言失败：{str(e)}")
        return

    # 发送操作反馈
    await matcher.send(f"已解除 {target_id} 的禁言，一定时间后将自动重新禁言")

    # 添加定时任务（30分钟后执行）
    scheduler.add_job(
        reban_job,
        "date",
        run_date=datetime.datetime.now() + datetime.timedelta(minutes=30),
        args=(group_id, target_id),
        id=f"reban_{group_id}_{target_id}"
    )


async def reban_job(group_id: int, user_id: int):
    try:
        # 重新禁言10天（864000秒）
        await get_bot().set_group_ban(
            group_id=group_id,
            user_id=user_id,
            duration=864000
        )
    except Exception as e:
        # 这里可以添加日志记录
        pass