from aiogram import Router, types #, F
from aiogram.filters import Command, Filter
# from aiogram.enums.chat_type import ChatType

from bot_api.Database.requests import (
    get_group_by_tg_id,
    is_student_leader,
    add_group,
    add_student,
    delete_student,
    update_leader,
    is_leader_here
)
from bot_api.Database.models import async_session


management_router = Router()

# region Фильтры
# Фильтр: группа должна быть создана
class IsGroupCreated(Filter):
    async def __call__(self, message: types.Message) -> bool:
        async with async_session() as session:
            grp = await get_group_by_tg_id(session, message.chat.id)
            return grp is not None

# Фильтр: только староста
class IsLeader(Filter):
    async def __call__(self, message: types.Message) -> bool:
        username = '@' + message.from_user.username
        async with async_session() as session:
            return await is_student_leader(session, username)

# Фильтр: старосты пока нет
class IsLeaderHere(Filter):
    async def __call__(self, message: types.Message) -> bool:
        async with async_session() as session:
            return await is_leader_here(session, message.chat.id)

# Фильтр: старосты пока нет или староста
class IsLeaderNotHereOrIsLeader(Filter):
    async def __call__(self, message: types.Message) -> bool:
        async with async_session() as session:
            leader_exists = await is_leader_here(session, message.chat.id)
            if not leader_exists:
                return True
            return await is_student_leader(session, '@' + message.from_user.username)
# endregion


# /create_group
@management_router.message(
    Command("create_group"),
    # F.chat.type == ChatType.PRIVATE
)
async def cmd_create_group(message: types.Message):
    amount = 5
    args = message.text.split(maxsplit=amount)

    if len(args) < amount:
        return await message.answer(
            "Использование:\n"
            "/create_group <название> <курс> <номер> <t.me/Username группы>\n\n"
            "Пример:\n"
            "/create_group \"ПМИ\" 4 1 https://t.me/YourGroupUsername"
        )

    _, name, course, number, link = args

    if link and link.startswith("https://t.me/"):
        # username = link.rstrip("/").split("/")[-1]
        # chat_obj = await message.bot.get_chat(username)
        tg_chat_id = message.chat.id

        from bot_api.Parsing import parse_schedule
        path_to_yaml_cfg = "bot_api\Parsing\config.yaml"

        number = int(number)
        course = int(course)

        schedule = await parse_schedule(path_to_yaml_cfg, name, number, course)

        async with async_session() as session:
            await add_group(
                session,
                group_tg_id=tg_chat_id,
                name=name,
                course=int(course),
                number=int(number),
                link=link,
                schedule=schedule
            )
        await message.answer(f"Группа «{name}» ({tg_chat_id}) создана.")
    else:
        return await message.answer("Ссылка на группу должна начинаться с 'https://t.me/'")

    return None


# /add_student
@management_router.message(
    Command("add_student"),
    # F.chat.type == ChatType.PRIVATE,
    IsGroupCreated(),
    IsLeaderNotHereOrIsLeader()
)
async def cmd_add_student(message: types.Message):
    amount = 5
    args = message.text.split(maxsplit=amount)

    if len(args) < amount:
        return await message.answer("Использование: /add_student <@username> <Фамилия> <Имя> <Староста>")
    _, username, surname, name, leader = args

    full_name = f"{surname} {name}"
    leader = (leader == '1')

    if username and username.startswith("@"):
        async with async_session() as session:
            result = await add_student(session, username=username, full_name=full_name, is_leader=leader, group_tg_id=message.chat.id)
        await message.answer(result)
    else:
        return await message.answer("Никнейм должен начинаться с '@'")

    return None


# /rm_student
@management_router.message(
    Command("rm_student"),
    # F.chat.type == ChatType.PRIVATE,
    IsGroupCreated(),
    IsLeaderNotHereOrIsLeader()
)
async def cmd_rm_student(message: types.Message):
    amount = 2
    args = message.text.split(maxsplit=amount)

    if len(args) < amount:
        return await message.answer("Использование: /rm_student <@username>")
    _, username = args

    if username and username.startswith("@"):

        async with async_session() as session:
            isl = await is_student_leader(session=session, username=username)
            if not isl:
                result = await delete_student(session, username)
                await message.answer(result)
            else:
                return await message.answer("Чтобы удалить старосту - его нужно переназначить")
    else:
        return await message.answer("Никнейм должен начинаться с '@'")

    return None


# /cd_leader
@management_router.message(
    Command("cd_leader"),
    # F.chat.type == ChatType.PRIVATE,
    IsGroupCreated(), IsLeader()
)
async def cmd_cd_leader(message: types.Message):
    amount = 2
    args = message.text.split(maxsplit=amount)

    if len(args) < amount:
        return await message.answer("Использование: /cd_leader <@username>")
    _, username = args

    if username and username.startswith("@"):
        async with async_session() as session:
            result = await update_leader(session, username)
        await message.answer(result)
    else:
        return await message.answer("Никнейм должен начинаться с '@'")

    return None