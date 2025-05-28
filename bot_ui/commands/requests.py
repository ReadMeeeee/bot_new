from aiogram import Router, types, F
from aiogram.filters import Command, Filter
# from aiogram.enums.chat_type import ChatType
from config import API_DS, model_url, model_name
from bot_api.Database.requests import get_group_field, get_group_by_tg_id
from bot_api.Database.models import async_session

from bot_api.AI import AIModelAPI

from bot_api.parsing.parsers import format_schedule, parse_format_news


requests_router = Router()


class IsGroupCreated(Filter):
    async def __call__(self, message: types.Message) -> bool:
        async with async_session() as session:
            grp = await get_group_by_tg_id(session, message.chat.id)
            return grp is not None


# /get_schedule, /get_events, /get_news, /get_hw, /bot
@requests_router.message(
    Command("get_schedule"),
    F.chat.type.in_({"group","supergroup"}),
    IsGroupCreated()
)
async def cmd_get_schedule(message: types.Message):
    """

    """
    amount = 2
    args = message.text.split(maxsplit=amount)
    days = {
            'понедельник',
            'вторник',
            'среда',
            'четверг',
            'пятница',
            'суббота',
    }

    day = None
    answer = "Не забывайте, что можно указать: \n/get_schedule <День недели> (опционально)\n\n"
    if len(args) == amount:
        answer = ""
        _, day = args
        day = day.lower()
        if day not in days:
            await message.answer("Укажите корректный день недели (понедельник - суббота)")
            return None

    async with async_session() as session:
        schedule = await get_group_field(session, message.chat.id, "schedule")
        schedule = await format_schedule(schedule, day)

    answer += schedule
    await message.answer(answer)
    return None


@requests_router.message(
    Command("get_events"),
    F.chat.type.in_({"group","supergroup"}),
    IsGroupCreated()
)
async def cmd_get_events(message: types.Message):
    async with async_session() as session:
        events = await get_group_field(session, message.chat.id, "events")

    if events is None:
        events = "Ближайших событий нет"

    await message.answer(events)


@requests_router.message(
    Command("get_hw"),
    F.chat.type.in_({"group", "supergroup"}),
    IsGroupCreated()
)
async def cmd_get_homework(message: types.Message):
    async with async_session() as session:
        homework = await get_group_field(session, message.chat.id, "homework")

    if homework is None:
        homework = "Ближайших событий нет"

    await message.answer(homework)


@requests_router.message(
    Command("get_news"),
    F.chat.type.in_({"group","supergroup"}),
    IsGroupCreated()
)
async def cmd_get_schedule(message: types.Message):
    async with async_session() as session:
        path_to_yaml_cfg = "bot_api\\parsing\\config.yaml"
        news = await parse_format_news(path_to_yaml_cfg)
        news = str(news)

    await message.answer(news)


from bot_api.AI.agent import Agent
from bot_api.AI.models.instructions_loader import load_instruction
from bot_api.AI.models.models import InstructionBlock
@requests_router.message(
    Command("bot"),
    F.chat.type.in_({"group","supergroup"}),
    IsGroupCreated()
)
async def cmd_bot(message: types.Message):
    model = AIModelAPI(API_DS, model_url, model_name)
    path_to_instructions = "bot_api/AI/models/instructions/instructions.json"
    instructions = load_instruction(path_to_instructions, InstructionBlock)

    agent = Agent(model, instructions)

    user_text = message.text.lstrip('/')
    result = await agent.run(user_text, message.chat.id)

    await message.answer(result)
    """
async def cmd_bot(message: types.Message):

    path_to_yaml_cfg = "bot_api/parsing/config.yaml"
    path_faiss = "bot_api/AI/embeddings_data/faiss_index"

    model = AIModelAPI(API_DS, model_url, model_name)
    group_id = message.chat.id

    result = await handle_define(model, message.text[1:], group_id, path_faiss, path_to_yaml_cfg)

    await message.answer(result)
    return None
"""