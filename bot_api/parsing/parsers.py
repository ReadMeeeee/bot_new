from bot_api.parsing.parsers_utils import *
import urllib.parse


# TODO переделать через os
PATH_TO_YAML = "C:\\Users\\Admin\\PycharmProjects\\TG_bot\\bot_api\\parsing\\config.yaml"


# Парсинг информации/ новостей/ расписания
async def parse_info_data(path_to_yaml_cfg: str) -> list[str]:
    """
    Функция парсинга основной информации университета и факультета

    :param path_to_yaml_cfg: Путь к конфигу для парсинга
    :return: Список различной информации
    """
    total_data = []
    config = await load_config(path_to_yaml_cfg)
    headers = config["parsers"]["headers"]
    websites = config["websites"]
    for site, site_config in websites.items():

        base_url = site_config['base_url']
        print(f"\n\nОбработка сайта: {site} ({base_url})")

        pages = site_config.get('pages', {})

        # Обработка информационных страниц (data)
        for page in pages.get('data', []):
            url = base_url + page['path']
            print(f"Парсинг data-страницы '{page['name']}' по URL: {url}")

            html = await fetch_page(url, headers)
            soup = BeautifulSoup(html, 'html.parser')
            data = await parse_selectors(soup, page['selectors'])

            total_data.append(data)
            print("Полученные данные:", data)

    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # parent_dir = os.path.abspath(os.path.join(script_dir, ".."))
    # file_path = os.path.join(parent_dir, "AI", "embeddings_data", "json_data", "sfedu_mmcs_data.json")

    # with open(file_path, "w", encoding="utf-8") as f:
    #     json.dump(total_data, f, ensure_ascii=False, indent=4)

    return total_data


async def parse_news_data(path_to_yaml_cfg: str = PATH_TO_YAML) -> list[dict]:
    """
    Парсит только первую страницу новостей из конфига и возвращает список новостей.

    :param path_to_yaml_cfg: Путь к конфигу для парсинга
    :return: Список новостей, где каждый элемент — dict с ключами: title, date, text, link, image
    """
    total_data_news = []

    config = await load_config(path_to_yaml_cfg)
    headers = config["parsers"]["headers"]
    websites = config["websites"]

    for site_cfg in websites.values():
        base_url = site_cfg['base_url']

        # Берём только первую новостную страницу
        news_pages = site_cfg.get('pages', {}).get('news', [])[:1]
        for page in news_pages:
            page_url = urllib.parse.urljoin(base_url, page['path'])
            html = await fetch_page(page_url, headers)
            soup = BeautifulSoup(html, 'html.parser')
            container = soup.select_one(page.get('container'))
            if container is None:
                continue

            items = container.select(page.get('item_selector'))
            for item in items:
                news = await parse_item(item, page['selectors'])
                if not isinstance(news, dict):
                    continue

                # Если ссылка относительная, склеиваем с base_url
                link = news.get('link', '')
                full_link = urllib.parse.urljoin(base_url, link)
                news['link'] = full_link

                total_data_news.append(news)

    return total_data_news


async def parse_format_news(path_to_yaml_cfg: str) -> str:
    """
    Форматирует список новостей в одну строку, где каждая новость — это заголовок и ссылка через перенос строки.
    Пропускает новости без заголовка (title None или пустая строка).

    :param path_to_yaml_cfg: Путь к конфигу для парсинга
    :return: Строка для отправки в Telegram
    """
    items = await parse_news_data(path_to_yaml_cfg)
    if not items:
        return "Новости не найдены."

    lines = []
    for entry in items:
        raw_title = entry.get("title")

        if raw_title is None or not raw_title.strip():
            continue

        link = entry.get("link", "")
        lines.append(f"{raw_title}\n{link}")

    if not lines:
        return "Нет новостей с заголовками."

    return "Новости МехМата и ЮФУ:\n\n" + "\n\n".join(lines)


async def parse_schedule(path_to_yaml_cfg: str,
                   group='ПМИ',
                   number=1,
                   course=1
) -> dict[str, str] | str:
    """
    Функция парсинга расписания

    :param path_to_yaml_cfg:  Путь к конфигу для парсинга
    :param group: Название курса
    :param number: Номер группы
    :param course: Курс
    :return: Словарь расписания, где дни недели - ключи.
    """
    config = await load_config(path_to_yaml_cfg)
    websites = config["websites"]

    base_url = websites['MMCS_schedule']['base_url']
    base_url = base_url + str(course)

    response = requests.get(base_url)
    response.raise_for_status()

    data = response.json()

    groups = [g for g in data['groups'] if g['name'] == group and g.get('grorder') == number]
    if not groups:
        return f"Группа '{group}' с номером {number} не найдена."

    # Собираем ID найденных групп
    group_ids = [g['id'] for g in groups]

    # Отбираем занятия для этих групп
    lessons = [lesson for lesson in data['lessons'] if lesson['groupid'] in group_ids]

    # Создаём словарь для расписания по дням (0 - понедельник, 5 - суббота)
    schedule = {i: [] for i in range(6)}

    for lesson in lessons:
        # Парсим время занятия
        timeslot = lesson['timeslot'].strip('()')
        parts = [part.strip() for part in timeslot.split(',')]
        if len(parts) < 4:
            continue  # Пропускаем некорректный формат

        day_of_week = int(parts[0])
        start_time = parts[1]
        end_time = parts[2]

        # Обрабатываем все учебные планы
        for subnum in range(1, lesson['subcount'] + 1):
            curriculum = next(
                (c for c in data['curricula'] if c['lessonid'] == lesson['id'] and c['subnum'] == subnum),
                None
            )
            if curriculum:
                entry = {
                    'start': start_time,
                    'end': end_time,
                    'subject': curriculum['subjectabbr'],
                    'teacher': curriculum['teachername'],
                    'room': curriculum['roomname'],
                    'info': lesson['info']
                }
                schedule[day_of_week].append(entry)

    # Сортируем занятия в каждом дне по времени начала
    for day_num in schedule:
        schedule[day_num].sort(key=lambda x: x['start'])

    async def format_schedule(sched):
        res = {
            'понедельник': '',
            'вторник': '',
            'среда': '',
            'четверг': '',
            'пятница': '',
            'суббота': '',
        }

        days_dict = {
            0: 'понедельник',
            1: 'вторник',
            2: 'среда',
            3: 'четверг',
            4: 'пятница',
            5: 'суббота',
        }

        def format_day(day_list):
            day_string = ''
            for i in day_list:
                pair = (' ' +
                        i['start'] + '-' + i['end'] + '\n ' +
                        i['subject'] + '\n ' +
                        i['teacher'] + '\n ' +
                        i['room'] + '\n\n'
                        )
                day_string += pair
            return day_string

        for i in sched:
            day = days_dict[i]
            if sched[i]:
                res[day] = '\n' + format_day(sched[i]) + '\n'
                # print(day, res[day])
            else:
                res[day] = '\n' + ' не учимся' '\n'
                # print(day, res[day])
        return res


    result = await format_schedule(schedule)

    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # parent_dir = os.path.abspath(os.path.join(script_dir, ".."))
    # file_path = os.path.join(parent_dir, "AI", "embeddings_data", "json_data", "schedule.json")

    # with open(file_path, "w", encoding="utf-8") as f:
    #     json.dump(result, f, ensure_ascii=False, indent=4)

    return result


async def format_schedule(schedule, day=None):
    result = ""
    if not day:
        for i in schedule:
            result += i + '\n' + schedule[i] + '\n\n'
    else:
        result += day + '\n' + schedule[day] + '\n\n'
    return result


"""
async def main():
    schedule = await parse_schedule(path_to_yaml_cfg='instructions.yaml',
                                    group='ПМИ', number=1, course=4)
    print(schedule)
    schedule = await format_schedule(schedule)
    print(schedule)


import asyncio
if __name__ == '__main__':
    asyncio.run(main())
"""
