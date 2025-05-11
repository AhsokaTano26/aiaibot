from nonebot.log import logger
from nonebot_plugin_orm import get_session

from .models_method import DetailManger

async def get_folder_name(msg):
    async with (get_session() as db_session):
        try:
            sheet = await DetailManger.get_all_student_id(db_session)
            for id in sheet:
                data = await DetailManger.get_Sign_by_student_id(db_session, id)
                if msg == data.extra_name:
                    return data.folder_name
            return None
        except Exception as e:
            logger.error(f"⚠️ 数据库操作失败：{str(e)}")


async def get_all_folder_names():
    async with (get_session() as db_session):
        try:
            msg = "所有名称列表：\n"
            sheet = await DetailManger.get_all_student_id(db_session)
            folder_name = []
            for id in sheet:
                data = await DetailManger.get_Sign_by_student_id(db_session, id)
                if data.folder_name not in folder_name:
                    msg += f"{data.folder_name}\n"
                    folder_name.append(data.folder_name)
            return msg
        except Exception as e:
            logger.error(f"⚠️ 数据库操作失败：{str(e)}")

async def get_all_folder_extra_names(folder_name):
    async with (get_session() as db_session):
        try:
            msg = f"{folder_name}所有名称列表：\n"
            sheet = await DetailManger.get_all_student_id(db_session)
            for id in sheet:
                data = await DetailManger.get_Sign_by_student_id(db_session, id)
                if data.folder_name == folder_name:
                    msg += f"{data.extra_name}\n"
            return msg
        except Exception as e:
            logger.error(f"⚠️ 数据库操作失败：{str(e)}")