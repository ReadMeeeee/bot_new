import datetime, string

from .embedding_manager import load_embedding_db, get_best_match
from .models import (
    AIModelLocal, AIModelAPI,
    role_news, instructions_news,
    role_classification, instructions_classification,
    role_fallback, instructions_fallback,
    role_schedule, instructions_schedule
)

from bot_api.Database import async_session, get_group_field
from bot_api.Parsing import parse_news_data


# Функция-конструктор запроса (роль + инструкция + сообщение)
async def just_response(model: AIModelLocal | AIModelAPI,
                        role: str,
                        instructions: str,
                        message: str,
                        max_tokens: int
) -> str:
    """
            Функция для генерации ответа на запрос к ИИ

            :param model: Модель ИИ (по API или локальная)
            :param role: Роль для ИИ
            :param message: Строка с сообщением пользователя
            :param instructions: Инструкция для обработки текста при помощи ИИ
            :param max_tokens: Максимальное количество токенов в ответе

            :return: Строка со сгенерированным ответом
            """
    response = model.get_response(
        message=message,
        instruction=instructions,
        role=role,
        max_tokens=max_tokens,
        temperature=0.1,
        # sampling=True # Для локальных моделей
    )

    return response


async def filter_news(model: AIModelLocal | AIModelAPI, news_list: list[dict]):
    """
    Фильтрует и возвращает новости, актуальные для студентов

    :param model: Модель ИИ, которая обрабатывает новости по релевантности студентам
    :param news_list: Список новостей (каждая новость — словарь с ключами: title, date, text, link, image)
    :return: Список новостей, релевантных для студентов
    """

    relevant_news = []

    for news in news_list:
        title = news.get('title', '')


        response = await just_response(
            model=model,
            role=role_news,
            instructions=instructions_news,
            message=title,
            max_tokens=2
        )

        if response.strip().lower() == "true":
            relevant_news.append(news)

    if not relevant_news:
        relevant_news.append("Интересных новостей пока нет")

    return relevant_news


# region Извлечение/ получение данных
async def get_schedule(category: list[str], group_id: int) -> str:
    """
    Возвращает расписание на указанные дни или на всю неделю.
    category[0] == 'расписание', далее — список дней в любом формате.
    """
    week_days = ['понедельник','вторник','среда','четверг','пятница','суббота','воскресенье']
    relative = {'завтра':1,'послезавтра':2}

    # Получаем из БД
    async with async_session() as session:
        raw = await get_group_field(session, group_id, 'schedule')
    if not isinstance(raw, dict):
        return "Расписание для группы ещё не загружено."
    sched = {k.lower(): v for k,v in raw.items()}

    def resolve(tkn: str) -> str | None:
        t = tkn.lower()
        if t in week_days: return t
        if t in relative:
            idx = (datetime.datetime.now().weekday() + relative[t]) % 7
            return week_days[idx]
        for fmt in ("%d.%m.%Y","%d.%m"):
            try:
                dt = datetime.datetime.strptime(t, fmt)
                if fmt=="%d.%m":
                    dt = dt.replace(year=datetime.datetime.now().year)
                return week_days[dt.weekday()]
            except ValueError:
                pass
        return None

    # строим список дней
    if len(category)<2:
        days = week_days[:-1]  # Пн–Сб
    else:
        days = []
        for tok in category[1:]:
            day = resolve(tok)
            if day == 'воскресенье':
                return (
                    "Пожалуйста, ознакомьтесь с актуальным расписанием занятий:\n"
                    "В воскресенье пар не бывает."
                )
            if day:
                if day not in days:
                    days.append(day)
            #else:
            #    days.append(f"неверный формат: «{tok}»")

    # Форматируем вывод
    header = "Пожалуйста, ознакомьтесь с актуальным расписанием занятий:\n\n"
    parts = []
    for d in days:
        if d.startswith("неверный формат"):
            parts.append(d)
        else:
            raw_day = sched.get(d,"").strip()
            if raw_day:
                parts.append(f"{d.capitalize()}:\n{raw_day}")
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
    return (f"Не пропустите предстоящие события и мероприятия:"
            f"\n{events}")


async def get_news(model: AIModelLocal | AIModelAPI, path_to_yaml_cfg: str) -> str:
    """
    Функция запроса на события к БД по group_id

    :param model: Модель ИИ (по API или локальная)
    :param path_to_yaml_cfg: Путь к .yaml файлу разметки
    :return: Строка с новостями университета и факультета
    """
    news = await parse_news_data(path_to_yaml_cfg=path_to_yaml_cfg)

    relevant_news = await filter_news(model, news)

    news_filtered = ""
    for i in relevant_news:
        news_filtered += ('Новость: ' + i['title'] +
                          '\nСсылка: ' + i['link'] + '\n\n')

    return news_filtered


async def get_fallback(model: AIModelLocal | AIModelAPI,
                       role: str,
                       message: str,
                       path_faiss: str,
                       max_tokens=450
) -> str:
    """
    Функция ответа на неклассифицированный запрос

    :param model: Модель ИИ (по API или локальная)
    :param role: Роль для ИИ
    :param message: Строка с сообщением пользователя
    :param path_faiss: Путь к векторной базе данных факультета
    :param max_tokens: Максимальное количество токенов в ответе (по умолчанию 300)
    :return: Строка со сгенерированным ответом
    """
    db = await load_embedding_db(path_faiss)
    relevant_data = await get_best_match(db, message)

    instructions_fb = await instructions_fallback(relevant_data, message, max_tokens=max_tokens)

    response = await just_response(
        model=model,
        role=role,
        instructions=instructions_fb,
        message=message,
        max_tokens=max_tokens
    )
    return response
# endregion


# Полная обработка запроса
async def handle_define(
        model: AIModelLocal | AIModelAPI,
        message: str,
        group_id,
        path_faiss: str,
        path_to_yaml_cfg: str
) -> str:
    """
    Функция обработки запроса (определение темы -> решение запроса по теме)

    :param model: Модель ИИ (по API или локальная)
    :param message: Строка с сообщением пользователя
    :param group_id: id группы
    :param path_faiss: Путь к векторной базе данных факультета
    :param path_to_yaml_cfg: Путь к .yaml файлу разметки
    :return: Строка с полноценным ответом на сообщение
    """

    # Классификация запроса
    cat = (await just_response(
        model, role_classification, instructions_classification,
        message, max_tokens=10
    )).lower()

    if cat == "расписание":
        # 2) Просим LLM выделить дни из запроса
        days_str = await just_response(
            model, role_schedule, instructions_schedule,
            message, max_tokens=32
        )
        # Чистим и разбиваем на токены
        tokens = [
            tok.strip(string.punctuation).lower()
            for tok in days_str.split()
            if tok.strip(string.punctuation)
        ]
        # Вызовем основную функцию
        return await get_schedule(["расписание", *tokens], group_id)

    # 3) Остальные категории
    if cat == "новости":
        return await get_news(model, path_to_yaml_cfg)
    if cat == "события":
        return await get_events(group_id)
    if cat in ("домашнее задание", "дз"):
        return await get_homework(group_id)
    # фоллбэк
    return await get_fallback(model, role_fallback, message, path_faiss)


"""
# Просто тесты
import asyncio, os
async def main():
    from config import API_AI, model_url, model_name


    model = AIModelAPI(API_AI, model_url, model_name)

    group_id = "test_group_id"

    parent_parent_dir = os.path.dirname(os.path.abspath(__file__))

    parent_faiss_dir = os.path.join(parent_parent_dir, "embeddings_data")
    path_faiss = os.path.join(parent_faiss_dir, "faiss_index")

    base_dir = os.path.dirname(parent_parent_dir)
    parent_cfg_dir = os.path.join(base_dir, "Parsing")
    path_cfg = os.path.join(parent_cfg_dir, "config.yaml")

    test_messages = [
        "Расскажи про магистратуру",
       # "Ты живой?",
       # "Что по новостям?"#, "Покажи расписание" # Только при полноценном запуске тк нужна БД
    ]


    for msg in test_messages:
        result = await handle_define(model, msg, group_id, path_faiss, path_cfg)
        print(f"Ответ на '{msg}':\n{result}\n")


if __name__ == '__main__':
    asyncio.run(main())
"""
