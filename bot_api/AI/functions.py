import datetime

# from .embedding_manager import load_embedding_db, get_best_match
from bot_api.AI.models import AIModelAPI
from bot_api.AI.models.models import InstructionBlockNews, LLMRequest, PrePrompt
from bot_api.AI.models.instructions_loader import load_instruction

from bot_api.Database import async_session, get_group_field
from bot_api.parsing import parse_news_data


# region Извлечение/ получение данных
async def get_schedule(ds: list[str], group_id: int):
    """
    Возвращает расписание на указанные дни или на всю неделю.
    :param ds: Список строк — дней или дат ("понедельник", "завтра", "15.05" и т.п.).
               Если пуст или None — распечатываем всю неделю.
    :param group_id: ID группы в БД.
    :return: Готовая многострочная строка с расписанием.
    """

    week_days = ['понедельник','вторник','среда','четверг','пятница','суббота']
    relative = {'завтра': 1, 'послезавтра': 2}

    def resolve_day(unresolved):
        """Преобразует токен в один из week_days или None."""
        d = unresolved.lower().strip()
        if d in week_days:
            return d
        if d in relative:
            idx = (datetime.datetime.now().weekday() + relative[d]) % 7
            return week_days[idx]
        for fmt in ("%d.%m.%Y", "%d.%m"):
            try:
                dt = datetime.datetime.strptime(d, fmt)
                if fmt == "%d.%m":
                    dt = dt.replace(year=datetime.datetime.now().year)
                return week_days[dt.weekday()]
            except ValueError:
                continue
        return None

    # Загрузка расписания из БД
    async with async_session() as session:
        raw = await get_group_field(session, group_id, 'schedule')
    if not isinstance(raw, dict):
        return "Расписание для группы ещё не загружено."
    sched = {day.lower(): text for day, text in raw.items()}

    # Определение дней из "Дано"
    days = []
    if not ds:
        days = week_days.copy()
    else:
        for token in ds:
            day = resolve_day(token)
            if day == 'воскресенье':
                return "В воскресенье занятий нет."
            if day and day not in days:
                days.append(day)
        if not days:
            return "Не удалось распознать ни одного корректного дня."

    # Финальная сборка овтета
    header = "Пожалуйста, ознакомьтесь с актуальным расписанием занятий:\n\n"
    parts = []
    for d in days:
        text = sched.get(d, "").strip()
        if text:
            parts.append(f"{d.capitalize()}:\n{text}")
        else:
            parts.append(f"{d.capitalize()}:\n  Нет занятий")

    return header + "\n\n".join(parts)



async def get_homework(group_id: int) -> str:
    """
    Функция запроса на домашнее задание к БД по group_id

    :param group_id: id группы

    :return: Строка с домашним заданием группы
    """
    async with async_session() as session:
        homework = await get_group_field(session=session, group_tg_id=group_id, field='homework')
    return (f"Информация по домашним заданиям:"
            f"\n{homework}")


async def get_events(group_id: int) -> str:
    """
    Функция запроса на события к БД по group_id

    :param group_id: id группы

    :return: Строка с событиями группы
    """
    async with async_session() as session:
        events = await get_group_field(session=session, group_tg_id=group_id, field='events')
    return (f"Не пропустите предстоящие мероприятия:"
            f"\n{events}")


async def get_news(model: AIModelAPI, path_to_instructions: str) -> str:
    """
    Функция запроса на события к БД по group_id

    :param model: Модель ИИ (по API или локальная)

    :return: Строка с новостями университета и факультета
    """
    news = await parse_news_data()

    instructions = load_instruction(path_to_instructions, InstructionBlockNews)
    instructions = instructions.to_pre_prompt()


    async def filter_news(model: AIModelAPI, instructions: PrePrompt, news_list: list[dict]):
        """
        Фильтрует и возвращает новости, актуальные для студентов

        :param model: Модель ИИ, которая обрабатывает новости по релевантности студентам
        :param news_list: Список новостей (каждая новость — словарь с ключами: title, date, text, link, image)
        :return: Строка с заголовками и ссылками релевантных новостей, разделённая двумя переводами строки
        """

        # Собираем вход для модели и параллельно data_news
        to_process = "\nНиже представлены 26 НОВОСТНЫХ ЗАГОЛОВКОВ ДЛЯ ОБРАБОТКИ:\n"
        data_news = []
        for new in news_list:
            title = (new.get('title') or "").strip()
            link = (new.get('link') or "").strip()
            entry = f"{title}\n{link}"

            data_news.append(entry)
            to_process += title + "\n\n"

        request = LLMRequest(role_instructions=instructions, task=to_process)
        relevant = await model.get_response(request)
        bits = relevant.strip()

        selected = []
        for bit, entry in zip(bits, data_news):
            if bit == '1':
                selected.append(entry)

        return "\n\n".join(selected)


    relevant_news = await filter_news(model=model, instructions=instructions, news_list=news)

    return relevant_news
# endregion

'''
import asyncio
async def main():
    from config import deepseek_api


    path_to_instructions = "C:\\Users\\Admin\\PycharmProjects\\TG_bot\\bot_api\\AI\\models\\instructions\\instructions_news.json"
    data = await get_news(model=deepseek_api, path_to_instructions=path_to_instructions)

    print(data)

if __name__ == '__main__':
    asyncio.run(main())
'''
