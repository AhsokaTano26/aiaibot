from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata
from nonebot import on_message, get_bot, logger
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    Message,
    MessageSegment
)
from nonebot.rule import Rule, to_me
from nonebot.matcher import Matcher
from nonebot.exception import ActionFailed
import asyncio
import re
from typing import Dict, Optional

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="fight",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

# 存储等待确认的决斗请求 {群号: 请求信息}
pending_duels: Dict[int, dict] = {}
# 存储进行中的决斗 {群号: 决斗信息}
ongoing_duels: Dict[int, dict] = {}
# 全局锁
duel_lock = asyncio.Lock()


def check_duel_command(event: GroupMessageEvent) -> bool:
    """改进的决斗命令检查，匹配/决斗开头的消息"""
    msg = event.get_plaintext().strip()
    return bool(re.match(r"^决斗", msg))


duel_rule = Rule(check_duel_command)
duel_matcher = on_message(rule=duel_rule, priority=10)


async def check_confirmation(event: GroupMessageEvent) -> bool:
    """检查是否是目标的确认消息"""
    # 只处理有等待确认的群
    if event.group_id not in pending_duels:
        return False

    # 检查发送者是否为被挑战者
    duel_info = pending_duels.get(event.group_id)
    if event.user_id != duel_info["target"]:
        return False

    # 支持多种确认方式
    msg = event.get_plaintext().strip().lower()
    return msg in {"接受", "确认", "y", "yes", "ok"}


confirm_matcher = on_message(rule=Rule(check_confirmation), priority=15)


@duel_matcher.handle()
async def handle_duel(event: GroupMessageEvent, matcher: Matcher):
    async with duel_lock:
        try:
            # 解析消息
            at_users = [
                seg.data["qq"]
                for seg in event.message
                if seg.type == "at" and str(seg.data["qq"]) != str(event.self_id)
            ]
            if not at_users:
                await matcher.finish("需要@你要决斗的对手！")

            target_id = int(at_users[0])
            group_id = event.group_id
            starter_id = event.user_id

            # 检查自我决斗
            if starter_id == target_id:
                await matcher.finish("你不能和自己决斗！")

            # 检查已有决斗
            if group_id in pending_duels or group_id in ongoing_duels:
                await matcher.finish("当前已有进行中的决斗请求！")

            # 保存等待确认的决斗
            pending_duels[group_id] = {
                "starter": starter_id,
                "target": target_id,
                "expire_task": None
            }

            # 发送确认请求
            await matcher.send(
                MessageSegment.at(target_id) +
                Message(f" 你被发起了决斗挑战！\n"
                        "请发送【接受】来确认决斗（30秒内有效）\n"
                        "超时未确认将自动取消")
            )

            # 设置30秒确认超时
            async def confirmation_timeout():
                await asyncio.sleep(30)
                async with duel_lock:
                    if group_id in pending_duels:
                        del pending_duels[group_id]
                        await matcher.send(
                            MessageSegment.at(starter_id) +
                            Message(" 的决斗请求已超时取消")
                        )

            pending_duels[group_id]["expire_task"] = asyncio.create_task(confirmation_timeout())

        except Exception as e:
            logger.error(f"决斗请求异常: {str(e)}")
            await matcher.finish("决斗请求处理失败，请稍后再试")


async def duel_start_task(group_id: int, matcher: Matcher):
    """开始决斗的定时任务"""
    await asyncio.sleep(5)
    async with duel_lock:
        if group_id not in ongoing_duels:
            return

        # 更新可开枪状态
        ongoing_duels[group_id]["can_shoot"] = True
        await matcher.send("🔥 开始！")

        # 设置30秒超时
        async def timeout_task():
            await asyncio.sleep(30)
            async with duel_lock:
                if group_id in ongoing_duels:
                    del ongoing_duels[group_id]
                    await matcher.send("🕒 决斗超时，自动取消！")

        ongoing_duels[group_id]["expire_task"] = asyncio.create_task(timeout_task())


@confirm_matcher.handle()
async def handle_confirmation(event: GroupMessageEvent, matcher: Matcher):
    async with duel_lock:
        try:
            group_id = event.group_id
            duel_info = pending_duels.get(group_id)

            if not duel_info:
                return

            # 取消确认超时任务
            if duel_info["expire_task"] and not duel_info["expire_task"].cancelled():
                duel_info["expire_task"].cancel()

            # 初始化决斗状态
            ongoing_duels[group_id] = {
                "starter": duel_info["starter"],
                "target": duel_info["target"],
                "can_shoot": False,  # 新增开枪许可状态
                "expire_task": None
            }
            del pending_duels[group_id]

            # 发送倒计时提示
            await matcher.send(
                Message("⚔ 决斗确认！\n") +
                MessageSegment.at(duel_info["starter"]) +
                Message(" vs ") +
                MessageSegment.at(duel_info["target"]) +
                Message("\n5秒后开始，提前开枪将直接判负！")
            )

            # 启动开始计时任务
            asyncio.create_task(duel_start_task(group_id, matcher))

        except Exception as e:
            logger.error(f"确认处理异常: {str(e)}")
            await matcher.finish("决斗确认失败，请检查日志")


async def handle_early_shoot(shooter_id: int, group_id: int, matcher: Matcher):
    """处理提前开枪"""
    logger.info(f"处理群 {group_id} 的提前开枪")
    try:
            logger.info(f"处理群 {group_id} 的提前开枪")
            duel_info = ongoing_duels.get(group_id)
            if not duel_info:
                logger.debug("决斗已结束，无需处理")
                return

            # 立即清除状态防止重复处理
            if duel_info["expire_task"]:
                duel_info["expire_task"].cancel()
            del ongoing_duels[group_id]

            # 构建消息
            result_msg = MessageSegment.at(shooter_id) + Message(" 犯规！抢跑开枪！🚫\n")

            # 获取胜者信息
            winner_id = duel_info["starter"] if shooter_id == duel_info["target"] else duel_info["target"]
            result_msg += MessageSegment.at(winner_id) + Message(" 自动获胜！🎉")

            # 执行禁言
            bot = get_bot()
            try:
                member_info = await bot.get_group_member_info(
                    group_id=group_id,
                    user_id=shooter_id
                )
                if member_info["role"] == "member":
                    await bot.set_group_ban(
                        group_id=group_id,
                        user_id=shooter_id,
                        duration=120
                    )
                    result_msg += Message("\n⏳ 违规者已被禁言2分钟！")
                    logger.info(f"成功禁言用户 {shooter_id}")
                else:
                    result_msg += Message("\n⚠️ 管理成员违规，本次不予禁言")
            except ActionFailed as e:
                logger.error(f"禁言失败: {str(e)}")
                result_msg += Message("\n❌ 禁言失败（权限不足）")

            await matcher.send(result_msg)
            logger.info(f"提前开枪处理完成，群：{group_id}")

    except Exception as e:
            logger.error(f"提前开枪处理异常: {str(e)}")
            await matcher.finish("⚠️ 违规处理出错，请联系管理员")


# 改进的射击检查规则
async def shoot_checker(event: GroupMessageEvent) -> bool:
    if event.group_id not in ongoing_duels:
        return False

    # 支持多种指令格式和容错
    msg = event.get_plaintext().strip().lower()
    return any(keyword in msg for keyword in ["开枪", "开抢", "bang", "shoot"])

shoot_matcher = on_message(rule=Rule(shoot_checker), priority=15)

@shoot_matcher.handle()
async def handle_shoot(event: GroupMessageEvent, matcher: Matcher):
    async with duel_lock:
        try:
            group_id = event.group_id
            shooter_id = event.user_id

            if group_id not in ongoing_duels:
                return

            duel_info = ongoing_duels[group_id]
            participants = [duel_info["starter"], duel_info["target"]]
            # 检查是否允许开枪
            if not duel_info.get("can_shoot", False):
                logger.info(f"检测到提前开枪，用户：{shooter_id}")
                await handle_early_shoot(shooter_id, group_id, matcher)
                return
            else:
                # 转换为字符串比较避免类型问题
                if str(shooter_id) not in map(str, participants):
                    return

                # 取消超时任务
                if duel_info["expire_task"] and not duel_info["expire_task"].cancelled():
                    duel_info["expire_task"].cancel()
                    logger.debug(f"已取消群{group_id}的决斗超时任务")

                # 确定胜负
                winner_id = shooter_id
                loser_id = duel_info["target"] if shooter_id == duel_info["starter"] else duel_info["starter"]

                # 获取成员信息
                bot = get_bot()
                try:
                    member_info = await bot.get_group_member_info(
                        group_id=group_id,
                        user_id=loser_id
                    )
                    role = member_info.get("role", "member")
                except ActionFailed as e:
                    logger.warning(f"获取成员信息失败: {str(e)}")
                    role = "member"

                result_msg = (
                        MessageSegment.at(winner_id) +
                        Message(" 抢先开枪！🏆\n") +
                        MessageSegment.at(loser_id) +
                        Message(" 输了！")
                )

                # 禁言处理
                try:
                    if role == "member":
                        await bot.set_group_ban(
                            group_id=group_id,
                            user_id=loser_id,
                            duration=60
                        )
                        result_msg += Message("\n💢 失败者已被禁言1分钟！")
                        logger.info(f"成功禁言 {loser_id} 于群 {group_id}")
                    else:
                        result_msg += Message("\n👑 由于失败者是管理员/群主，本次不禁言！")
                except ActionFailed as e:
                    logger.error(f"禁言失败: {str(e)}")
                    result_msg += Message("\n⚠️ 禁言失败（权限不足）！")
                except Exception as e:
                    logger.error(f"未知错误: {str(e)}")
                    result_msg += Message("\n❌ 处理禁言时发生未知错误！")

            del ongoing_duels[group_id]
            await matcher.send(result_msg)
        except Exception as e:
            logger.error(f"开枪处理异常: {str(e)}")
            await matcher.finish("决斗结果处理失败，请检查日志")