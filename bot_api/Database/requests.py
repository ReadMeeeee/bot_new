from contextlib import asynccontextmanager
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot_api.Database.models import Student, Group


@asynccontextmanager
async def transactional_context(session: AsyncSession):
    """
    Асинхронный контекстный менеджер для выполнения транзакций.

    Если сессия уже в транзакции, создаётся вложенная транзакция (begin_nested),
    иначе открывается новая транзакция (begin).

    :param session: Асинхронная сессия SQLAlchemy
    :yields: Та же сессия для выполнения операций
    """
    if session.in_transaction():
        async with session.begin_nested():
            yield session
    else:
        async with session.begin():
            yield session


# region Группа: добавление/получение
async def add_group(
    session: AsyncSession,
    group_tg_id: int,
    name: str,
    course: int,
    number: int,
    link: str,
    schedule: dict = None,
    events: dict = None,
    homework: dict = None
) -> None:
    """
    Добавляет новую группу в базу данных.

    :param session: Асинхронная сессия SQLAlchemy
    :param group_tg_id: Уникальный Telegram ID группы
    :param name: Название группы
    :param course: Номер курса
    :param number: Номер группы
    :param link: Ссылка на группу в Telegram
    :param schedule: JSON-расписание группы (опционально)
    :param events: JSON-события группы (опционально)
    :param homework: JSON-домашние задания группы (опционально)
    :return: None
    """
    async with transactional_context(session):
        group = Group(
            group_tg_id=group_tg_id,
            group_name=name,
            group_course=course,
            group_number=number,
            tg_link=link,
            schedule=schedule,
            events=events,
            homework=homework
        )
        session.add(group)
    return None


async def get_group_by_tg_id(session: AsyncSession, group_tg_id: int):
    """
    Получает группу по её Telegram ID.

    :param session: Асинхронная сессия SQLAlchemy
    :param group_tg_id: Уникальный Telegram ID группы
    :return: Объект Group или None, если не найден
    """
    result = await session.execute(select(Group).filter_by(group_tg_id=group_tg_id))
    return result.scalar_one_or_none()
# endregion


# region Студент: загрузка/удаление/получение/проверка на старосту
async def add_student(
    session: AsyncSession,
    username: str,
    full_name: str,
    is_leader: bool,
    group_tg_id: int
) -> str:
    """
    Добавляет нового студента в указанную группу.

    :param session: Асинхронная сессия SQLAlchemy
    :param username: Уникальное имя пользователя Telegram (@username)
    :param full_name: Полное имя студента
    :param is_leader: Флаг старосты
    :param group_tg_id: Telegram ID группы, к которой привязан студент
    :raises ValueError: Если группа не найдена
    :return: Отладочный вывод
    """
    result = await session.execute(select(Group).filter_by(group_tg_id=group_tg_id))
    group = result.scalar_one_or_none()
    if not group:
        raise ValueError(f"Группа с group_tg_id={group_tg_id} не найдена")

    async with transactional_context(session):
        student = Student(
            student_username=username,
            student_full_name=full_name,
            student_is_leader=is_leader,
            group_id=group.id
        )
        session.add(student)

    return f"Студент {full_name} ({username[1:]}) добавлен."


async def delete_student(session: AsyncSession, username: str) -> str:
    """
    Удаляет студента по его Telegram username.

    :param session: Асинхронная сессия SQLAlchemy
    :param username: Имя пользователя Telegram (@username)
    :return: Сообщение о результате удаления
    """
    async with transactional_context(session):
        result = await session.execute(select(Student).filter_by(student_username=username))
        student = result.scalar_one_or_none()
        if student:
            await session.delete(student)
            return f"Студент {username[1:]} удален"
        return f"Студент {username[1:]} не найден"


async def get_students_by_group(session: AsyncSession, group_tg_id: int):
    """
    Возвращает список студентов, принадлежащих указанной группе.

    :param session: Асинхронная сессия SQLAlchemy
    :param group_tg_id: Telegram ID группы
    :return: Список объектов Student
    """
    req = (
        select(Student)
        .join(Group, Student.group_id == Group.id)
        .filter(Group.group_tg_id == group_tg_id)
    )
    result = await session.execute(req)
    return result.scalars().all()


async def get_student_by_username(session: AsyncSession, username: str):
    """
    Проверяет наличие студента по username и возвращает информацию о группе.

    :param session: Асинхронная сессия SQLAlchemy
    :param username: Имя пользователя Telegram (@username)
    :return: Строка с результатом поиска
    """
    result = await session.execute(
        select(Student).filter_by(student_username=username)
    )
    student = result.scalar_one_or_none()
    if student:
        return f"Студент {username[1:]} найден в группе {student.group.group_name}."
    return f"Студент {username[1:]} не найден."


async def is_student_leader(
    session: AsyncSession,
    username: str
) -> bool:
    """
    Проверяет, является ли указанный студент старостой своей группы.

    :param session: Асинхронная сессия SQLAlchemy
    :param username: Имя пользователя Telegram (@username)
    :return: True, если студент староста, иначе False
    :raises ValueError: если студент не найден в базе
    """
    result = await session.execute(
        select(Student).filter_by(student_username=username)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise ValueError(f"Студент {username} не найден")
    return student.student_is_leader
# endregion


# region Староста: обновление/ Проверка наличия
async def update_leader(session: AsyncSession, username: str) -> str:
    """
    Назначает указанного студента старостой, снимая этот статус с предыдущих.

    :param session: Асинхронная сессия SQLAlchemy
    :param username: Имя пользователя Telegram (@username)
    :return: Сообщение о результате операции
    """
    async with transactional_context(session):
        result = await session.execute(
            select(Student).filter_by(student_username=username)
        )
        student = result.scalar_one_or_none()

        if not student:
            return f"{username[1:]} не найден"

        result_leaders = await session.execute(
            select(Student)
            .where(
                Student.group_id == student.group_id,
                Student.student_is_leader == True
            )
        )
        current_leaders = result_leaders.scalars().all()
        for leader in current_leaders:
            leader.student_is_leader = False

        student.student_is_leader = True
        return f"{username[1:]} назначен старостой"


async def is_leader_here(session: AsyncSession, group_tg_id: int) -> bool:
    """
    Проверяет наличие старосты в группе по её Telegram ID.

    :param session: Асинхронная сессия SQLAlchemy
    :param group_tg_id: Telegram ID группы
    :return: True, если в этой группе уже есть староста
    """
    # Сначала находим внутренний ID группы
    result = await session.execute(
        select(Group.id).filter_by(group_tg_id=group_tg_id)
    )
    grp_id = result.scalar_one_or_none()
    if grp_id is None:
        return False

    # Проверяем, есть ли студент с флагом is_leader=True в этой группе
    result = await session.execute(
        select(Student.id)
        .filter_by(group_id=grp_id, student_is_leader=True)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None
# endregion


# region Универсальные запросы: ДЗ/события/расписание
async def get_group_field(session: AsyncSession, group_tg_id: int, field: str):
    """
    Возвращает JSON-поле заданного имени из группы.

    :param session: Асинхронная сессия SQLAlchemy
    :param group_tg_id: Telegram ID группы
    :param field: Имя поля ('schedule', 'events', 'homework')
    :return: Содержимое поля или None
    """
    result = await session.execute(select(Group).filter_by(group_tg_id=group_tg_id))
    group = result.scalar_one_or_none()
    if group and hasattr(group, field):
        return getattr(group, field)
    return None


async def update_group_field(session: AsyncSession,group_tg_id: int, field: str, value) -> str:
    """
    Обновляет указанное JSON-поле группы.

    :param session: Асинхронная сессия SQLAlchemy
    :param group_tg_id: Telegram ID группы
    :param field: Имя поля для обновления ('schedule', 'events', 'homework')
    :param value: Новое значение (dict или None)
    :return: Сообщение о результате операции
    """
    # Value = dict или None
    async with transactional_context(session):
        allowed_fields = {"schedule", "events", "homework"}
        if field not in allowed_fields:
            return "Недопустимое поле для изменения"

        result = await session.execute(
            select(Group).filter_by(group_tg_id=group_tg_id)
        )
        group = result.scalar_one_or_none()
        if group and hasattr(group, field):
            setattr(group, field, value)
            return f"Поле '{field}' обновлено для группы group_tg_id={group_tg_id}"
        return f"Группа с group_tg_id={group_tg_id} не найдена"
# endregion
