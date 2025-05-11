from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata
import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter, GROUP_ADMIN, GROUP_OWNER
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot import on_message, on_command
from nonebot.rule import Rule, to_me
from nonebot.typing import T_State
from pathlib import Path
from nonebot.adapters.onebot.v11 import (
    Adapter as OneBotV11Adapter,
    MessageEvent,
    MessageSegment,
    GroupMessageEvent,
    Message
)
from nonebot.params import CommandArg
import random
from nonebot.log import logger
from nonebot_plugin_orm import get_session

from .config import Config
from .encrypt import encrypt
from .models_method import DetailManger
from .models import Detail
from .foldername import get_folder_name, get_all_folder_names, get_all_folder_extra_names

__plugin_meta__ = PluginMetadata(
    name="images",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)



# 初始化 NoneBot
nonebot.init()

# 注册 OneBot V11 适配器
driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)

# 配置图片存储目录
BASE_IMAGE_DIR = Path("data/images").resolve()
BASE_IMAGE_DIR.mkdir(parents=True, exist_ok=True)


async def check_valid_folder(event: MessageEvent) -> bool:
    """检查消息是否为有效的图片文件夹名称"""
    folder_name = event.get_plaintext().strip()
    folder_name = await get_folder_name(folder_name)
    if not folder_name:
        return False

    target_dir = (BASE_IMAGE_DIR / folder_name).resolve()
    return (
            target_dir.exists()
            and target_dir.is_dir()
            and BASE_IMAGE_DIR in target_dir.parents
    )


# 创建消息处理器
matcher = on_message(rule=Rule(check_valid_folder), priority=10, block=True)


@matcher.handle()
async def handle_image_request(event: MessageEvent):
    folder_name = event.get_plaintext().strip()
    folder_name = await get_folder_name(folder_name)
    target_dir = BASE_IMAGE_DIR / folder_name
    # 支持的图片格式
    valid_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

    # 获取所有图片文件
    images = [
        f for f in target_dir.iterdir()
        if f.is_file() and f.suffix.lower() in valid_exts
    ]

    if not images:
        await matcher.finish(f"📂 文件夹 {folder_name} 中没有找到图片")

    # 随机选择一张图片
    selected_image = random.choice(images)

    try:
        # 读取图片并发送
        with open(selected_image, "rb") as f:
            image_data = f.read()
        await matcher.send(MessageSegment.image(image_data))
    except Exception as e:
        await matcher.finish(f"❌ 图片发送失败：{str(e)}")


async def validate_folder(folder_name: str) -> Path:
    """验证并返回安全的目标路径"""
    folder_name = re.sub(r'[\\/:*?"<>|]', "", folder_name.strip())  # 过滤非法字符
    target_dir = (BASE_IMAGE_DIR / folder_name).resolve()

    # 防止目录遍历攻击
    if BASE_IMAGE_DIR not in target_dir.parents:
        raise ValueError("非法路径")

    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir





def get_image_ext(content: bytes) -> str:
    """通过文件头识别图片格式"""
    if content.startswith(b"\xff\xd8"):
        return "jpg"
    elif content.startswith(b"\x89PNG"):
        return "png"
    elif content.startswith(b"GIF8"):
        return "gif"
    elif content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "webp"
    elif content.startswith(b"BM"):
        return "bmp"
    return "dat"




all_foldername = on_command("所有文件夹",priority=5, block=True)
@all_foldername.handle()
async def handle_all_image(event: MessageEvent, state: T_State):
    try:
        msg = await get_all_folder_names()
        await all_foldername.send(msg)
    except Exception as e:
        await all_foldername.finish(f"⚠️ 数据库操作失败：{str(e)}")

all_folder_extra_name = on_command("其他",priority=5, block=True)
@all_folder_extra_name.handle()
async def handle_all_image(args: Message = CommandArg()):
    command = args.extract_plain_text().strip()
    folder_name = str(command.split(" ")[0])
    try:
        msg = await get_all_folder_extra_names(folder_name)
        await all_foldername.send(msg)
    except Exception as e:
        await all_foldername.finish(f"⚠️ 数据库操作失败：{str(e)}")






from nonebot.adapters.onebot.v11 import (
    Adapter as OneBotV11Adapter,
    MessageEvent,
    MessageSegment,
    GroupMessageEvent,
    Message
)
from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.typing import T_State
import re
import httpx
import hashlib
import time

# 新增的图片保存处理器
save_image = on_command("存图", priority=5, block=True,permission=GROUP_ADMIN | GROUP_OWNER)


async def get_referenced_image(event: MessageEvent) -> list:
    """获取被引用消息中的图片链接"""
    if not event.reply:
        return []
    original_msg = event.reply.message
    return [seg.data["url"] for seg in original_msg if seg.type == "image"]


@save_image.handle()
async def handle_save_image(
        event: GroupMessageEvent,
        state: T_State,
        args: Message = CommandArg()
):
    # 仅处理群聊消息
    if not isinstance(event, GroupMessageEvent):
        await save_image.finish("⚠️ 请在群聊中使用存图功能")

    # 获取文件夹名称
    folder_name = args.extract_plain_text().strip()
    folder_name = await get_folder_name(folder_name)

    if folder_name !=None:
        folder_name = folder_name
    else:
        folder_name = args.extract_plain_text().strip()
    if not folder_name:
        await save_image.finish("📝 请使用格式：存图 文件夹名")

    # 验证文件夹名称
    try:
        target_dir = await validate_folder(folder_name)
    except ValueError:
        await save_image.finish("⚠️ 包含非法字符，请使用合法文件夹名称")


    try:
        async with (get_session() as db_session):
            true_folder_name = folder_name + "-" + folder_name
            id = await encrypt(true_folder_name)
            existing_lanmsg = await DetailManger.get_Sign_by_student_id(
                db_session, id)
            if existing_lanmsg:  # 更新记录
                logger.info(f"{folder_name}已存在")
            else:  # 创建新记录
                try:
                    # 写入数据库

                    print(id)
                    await DetailManger.create_signmsg(
                        db_session,
                        id=id,
                        folder_name=folder_name,
                        extra_name=folder_name
                    )
                    logger.info(f"创建文件夹数据: {folder_name}")
                except Exception as e:
                    await save_image.finish(f"⚠️ 数据库写入失败：{str(e)}")
    except Exception as e:
        await save_image.finish(f"⚠️ 数据库操作失败：{str(e)}")

    # 获取被引用的图片
    image_urls = await get_referenced_image(event)
    if not image_urls:
        await save_image.finish("⚠️ 请先引用包含图片的消息")

    # 保存图片
    success_count = 0
    async with httpx.AsyncClient(timeout=30) as client:
        for url in image_urls:
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                        continue

                # 生成安全文件名
                file_hash = hashlib.md5(resp.content).hexdigest()[:8]
                timestamp = int(time.time())
                file_ext = get_image_ext(resp.content)
                file_name = f"{timestamp}_{file_hash}.{file_ext}"

                # 保存文件
                save_path = target_dir / file_name
                with open(save_path, "wb") as f:
                    f.write(resp.content)

                success_count += 1
            except Exception as e:
                print(f"图片保存失败：{str(e)}")

    await save_image.finish(
        MessageSegment.at(event.user_id) +
        MessageSegment.text(f" ✅ 成功保存 {success_count} 张图片到 {folder_name}")
    )


extra_name_add = on_command("其他名称", priority=5, block=True,permission=GROUP_ADMIN | GROUP_OWNER)

@extra_name_add.handle()
async def handle_extra_name(event: MessageEvent, state: T_State,args: Message = CommandArg()):
    async with (get_session() as db_session):
        command = args.extract_plain_text().strip()
        folder_name = str(command.split(" ")[0])
        extra_name = str(command.split(" ")[1])
        try:
            existing_lanmsg = await get_folder_name(folder_name)
            if existing_lanmsg == None:
                await extra_name_add.send(f"⚠️ 文件夹 {folder_name} 不存在")
            else:
                id = await encrypt(folder_name + "-" + extra_name)
                try:
                    mag = await DetailManger.get_Sign_by_student_id(db_session, id)
                    if mag:
                        await extra_name_add.send(f"⚠️ 文件夹 {folder_name} 已存在其他名称 {extra_name}")
                        return
                    await DetailManger.create_signmsg(
                        db_session,
                        id=id,
                        folder_name=folder_name,
                        extra_name=extra_name
                    )
                    await extra_name_add.send(f"已为 {folder_name} 文件夹添加其他名称 {extra_name}")
                except Exception as e:
                    await extra_name_add.finish(f"⚠️ 数据库写入失败：{str(e)}")
        except Exception as e:
            await extra_name_add.finish(f"⚠️ 数据库操作失败：{str(e)}")


extra_name_delete = on_command("删除", priority=5, block=True, permission=GROUP_ADMIN | GROUP_OWNER)
@extra_name_delete.handle()
async def handle_extra_name(event: MessageEvent, state: T_State,args: Message = CommandArg()):
    async with (get_session() as db_session):
        command = args.extract_plain_text().strip()
        folder_name = str(command.split(" ")[0])
        extra_name = str(command.split(" ")[1])
        id = await encrypt(folder_name + "-" + extra_name)
        try:
            mag = await DetailManger.get_Sign_by_student_id(db_session, id)
            if not mag:
                await extra_name_delete.send(f"{folder_name} 文件夹的其他名称 {extra_name} 不存在")
            else:
                await DetailManger.delete_id(db_session, id)
                await extra_name_delete.send(f"已为 {folder_name} 文件夹删除其他名称 {extra_name}")
        except Exception as e:
            await extra_name_delete.finish(f"⚠️ 数据库操作失败：{str(e)}")


help = on_command("help", aliases={"帮助"},priority=5, block=True)
@help.handle()
async def handle_extra_name():
    msg = f"群图片bot使用指南：\n\
          1.上传的基本操作为：先引用所需上传的图片（支持上传一条信息里的多张图片），然后输入：存图 名称。\n\n\
          例如：存图 相羽爱奈（如有其他名称如：aiai，则可写为：存图 aiai）\n\n\
          2.在上传前请注意，发送如下指令：所有文件夹，以查询所要上传的nsy图片文件夹是否存在（所有文件夹均以声优本名命名）。\n\n\
          若不存在，则需在第一次上传该女声优图片时，名称填写为nsy的本名，bot将会创建相应的文件夹，例如：存图 相羽爱奈。\n\n\
          若存在，则支持使用nsy别名进行上传，例如：存图 aiai（aiai为已写入的相羽爱奈本名）。\n\n\
          3.别名查询方法，输入命令：其他 要查询的文件夹名，例如：其他 相羽爱奈\n\n\
          4.增加别名，输入命令：其他名称 文件夹名 其他名称，例如：其他 相羽爱奈 aiai\n\n\
          5。查询图片，支持本名和别名查询，直接输入，bot会随机从图片库选取图片并发送。\n\n\
          tips：上传女声优图片时，如果bot返回信息中，存到的文件夹名称不是女声优本名而是输入的别名，则表示新创建了一个文件夹。不要慌张，请及时联系@Tano，我会及时处理。\n\n\
          特别感谢@相羽友希奈·噶吃·凑爱奈为丰富图片库做出的努力！！！"
    await help.send(msg)