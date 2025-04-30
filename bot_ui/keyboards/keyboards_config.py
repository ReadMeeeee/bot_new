MENU_SECTIONS = {
    "base": {
        "title": "Основные",
        "items": [
            ("/start", "start", "Запустить бота и открыть главное меню"),
            ("/about", "about", "Узнать информацию о боте"),
            ("/help",  "help", "Показать справочную информацию"),
        ],
    },
    "group": {
        "title": "Управление группой",
        "items": [
            ("/create_group", "create_group", "Создать новую группу"),
            ("/change_group", "change_group", "Изменить данные существующей группы"),
            ("/add_student",  "add_student",  "Добавить студента в группу"),
            ("/rm_student",   "rm_student",   "Удалить студента из группы"),
            ("/cd_leader",    "cd_leader",    "Назначить старосту группы"),
        ],
    },
    "requests": {
        "title": "Групповые запросы",
        "items": [
            ("/get_schedule", "get_schedule", "Получить текущее расписание"),
            ("/get_events",   "get_events",   "Получить список ближайших событий"),
            ("/get_news",     "get_news",     "Вывести последние новости"),
            ("/get_hw",       "get_hw",       "Показать назначенные ДЗ"),

            ("/add_events",   "add_events",   "Добавить новое событие"),
            ("/add_hw",       "add_hw",       "Добавить домашнее задание"),
        ],
    },
    "ai": {
        "title": "🤖 Запрос к ИИ",
        "items": [
            ("/bot", "bot", "Задать вопрос нейросети"),
        ],
    },
}


from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def make_keyboard(
    prefix: str,
    section: str,
    include_back: bool = True,
    in_row: int = 2,
) -> InlineKeyboardMarkup:
    """
    Фабрика по созданию клавиатуры builderом по разметке config

    :param prefix: Префикс клавиатуры - меню: "menu" или "help"
    :param section: Ключ подменю: "base", "group", "requests", "ai"
    :param include_back: Включение кнопки "назад"
    :param in_row: Количество кнопок в ряду

    :return: Клавиатура InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    # Если главная — кнопки по секциям
    if section == "main":
        for sec_key, sec_data in MENU_SECTIONS.items():
            builder.button(
                text=sec_data["title"],
                callback_data=f"{prefix}:{sec_key}",
            )
    else:
        # Для любого другого раздела берём items из нужной секции
        section_data = MENU_SECTIONS[section]
        for text, key, _desc in section_data["items"]:
            builder.button(
                text=text,
                callback_data=f"{prefix}:{section}:{key}",
            )

    if include_back:
        if prefix == "help" and section == "main":
            builder.button(
                text="🔙 В главное меню",
                callback_data="menu:main"
            )
        else:
            builder.button(
                text="🔙 Назад",
                callback_data=f"{prefix}:main"
            )

    builder.adjust(in_row)
    return builder.as_markup()
