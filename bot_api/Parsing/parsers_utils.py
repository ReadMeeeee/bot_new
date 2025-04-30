import re, yaml, requests
from bs4 import BeautifulSoup


# Ассистенты парсинга
async def clear_text(text: str, to_lower: bool = False) -> str:
    """
    Функция очистки импортируемого со страниц текста
    (от специальных символов, лишних отступов и переходов)

    :param text: Текст для очистки
    :param to_lower: Булева переменная для уменьшения регистра
    :return: Строка с очищенным текстом
    """
    remove_chars = {
        0x00A0: None,  # NBSP – no-break space
        0x00AD: None,  # SHY  – soft hyphen
        0x200B: None  # ZWSP – zero width space
    }
    text = re.sub(r'\n+', '\n', text)
    text = text.translate(remove_chars)

    if to_lower:
        text = text.lower()

    return text


async def load_config(path="config.yaml"):
    """
    Функция загрузки .yaml конфига

    :param path: Путь к .yaml конфигу
    :return: Переменная с содержимым конфига
    """
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


async def fetch_page(url: str, headers: dict[str, str | None]) -> str:
    """
    Функция получения ответа на запрос с разметкой

    :param url: Ссылка на страницу
    :param headers: Необходимый фрагмент страницы
    :return: ответ на запрос
    """
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.text


async def parse_selectors(soup: BeautifulSoup, selectors: dict[str, str | None]) -> dict[str, str] | None:
    """
    Обрабатываем селекторы для одиночной страницы (data)

    :param soup: Инструмент парсинга
    :param selectors: Селекторы (ключи разметки)
    :return: Строковая переменная с содержимым по селектору
    """
    result = {}
    for key, selector in selectors.items():
        element = soup.select_one(selector)
        result[key] = element.text.strip() if element else None
        if result[key] is not None: result[key] = await clear_text(result[key], to_lower=True)

    return result


async def parse_item(item, selectors: dict[str, str | None]) -> dict[str, str] | None:
    """
    Обрабатываем каждый элемент в новостях (news)

    :param item:
    :param selectors:
    :return:
    """
    result = {}
    for key, selector_conf in selectors.items():
        # Если selector_conf – словарь, значит нужно извлечь атрибут
        if isinstance(selector_conf, dict):
            element = item.select_one(selector_conf.get("selector"))
            if element:
                # Если запрошено значение атрибута, берём его, иначе текст
                result[key] = element.get(selector_conf.get("attribute"), element.text.strip())
            else:
                result[key] = None
        else:
            element = item.select_one(selector_conf)
            result[key] = element.text.strip() if element else None
            if result[key] not in (None, 'link'): result[key] = await clear_text(result[key])

    return result
