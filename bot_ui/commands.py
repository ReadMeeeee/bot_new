from aiogram import types
from aiogram.filters import BaseFilter
from bot_api.Database.requests import get_group_by_tg_id, is_student_leader


from bot_ui.keyboards.handler import dp, bot



class IsGroupCreated(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        async with async_session() as session:
            grp = await get_group_by_tg_id(session, message.chat.id)
            return grp is not None

class IsLeader(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        # для лички мы смотрим message.from_user.username
        username = message.from_user.username
        async with async_session() as session:
            return await is_student_leader(session, username)


from aiogram import F
from aiogram.enums.chat_type import ChatType
from aiogram.filters import Command

from bot_api.Database.requests import add_group
from bot_api.Database.models import async_session

@dp.message(
    Command("create_group"),
    F.chat.type == ChatType.PRIVATE
)
async def cmd_create_group(message: types.Message):
    args = message.get_args().split()
    if len(args) < 4:
        return await message.answer(
            "Использование: /create_group <название> <курс> <номер> [ссылка]\n"
            "Пример:        /create_group \"ПМИ\" 4 1 https://t.me/joinchat/..."
        )


    name = args[0]
    course = int(args[1])
    number = int(args[2])
    link = args[3]

    username = link.rsplit("/", 1)[-1]
    chat = await bot.get_chat(username)
    tg_chat_id = chat.id

    async with async_session() as session:
        await add_group(
            session,
            group_tg_id=tg_chat_id,
            name=name,
            course=course,
            number=number,
            link=link
        )
    await message.answer(f"Группа «{name} {number}.{course}» ({tg_chat_id}) создана.")
    return None
