import pytest
from sqlalchemy import select
from bot_api.Database.models import Group, Student
from bot_api.Database import *


@pytest.mark.asyncio
async def test_add_group(session):
    tg_id = 123
    await add_group(
        session,
        group_tg_id=tg_id,
        name="ПМИ",
        course=2,
        number=3,
        link="https://t.me/example_group",
        schedule={"Понедельник": ["ИИ", "а"]}
    )

    result = await session.execute(
        select(Group).where(Group.group_tg_id == tg_id)
    )
    group = result.scalar_one()
    assert group.group_name == "ПМИ"
    assert group.schedule["Понедельник"] == ["ИИ", "а"]

@pytest.mark.asyncio
async def test_add_student(session):
    # Создаём группу вручную
    group = Group(
        group_tg_id=999,
        group_name="ФИИТ",
        group_course=1,
        group_number=1,
        tg_link="None",
        schedule={}
    )
    session.add(group)
    await session.commit()
    await session.refresh(group)

    # Добавляем студента через функцию
    await add_student(
        session,
        username="@ivan",
        full_name="Иван Иванов",
        is_leader=False,
        group_tg_id=999
    )

    result = await session.execute(
        select(Student).where(Student.student_username == "@ivan")
    )
    student = result.scalar_one()
    assert student.student_full_name == "Иван Иванов"
    assert student.group_id == group.id

@pytest.mark.asyncio
async def test_get_student_by_username(session):
    # Создаём группу и студента
    group = Group(
        group_tg_id=1245,
        group_name="Some Group",
        group_course=1,
        group_number=1,
        tg_link="link",
        schedule={}
    )
    session.add(group)
    await session.commit()
    await session.refresh(group)

    await add_student(
        session,
        username="@student",
        full_name="Имя Фамилия",
        is_leader=False,
        group_tg_id=1245
    )

    msg = await get_student_by_username(session, username="@student")
    assert "найден" in msg

    # Повторная попытка поиска несуществующего
    msg2 = await get_student_by_username(session, username="@student1")
    assert "не найден" in msg2

@pytest.mark.asyncio
async def test_get_group_by_tg_id(session):
    tg_id = 111
    await add_group(
        session,
        group_tg_id=tg_id,
        name="Test Group",
        course=1,
        number=1,
        link="test_link",
        schedule={"Понедельник": []}
    )
    group = await get_group_by_tg_id(session, group_tg_id=tg_id)
    assert group is not None
    assert group.group_name == "Test Group"

@pytest.mark.asyncio
async def test_delete_student(session):
    # Создаём группу и студента
    group = Group(
        group_tg_id=12345,
        group_name="Some Group",
        group_course=1,
        group_number=1,
        tg_link="link",
        schedule={}
    )
    session.add(group)
    await session.commit()
    await session.refresh(group)

    await add_student(
        session,
        username="@student2",
        full_name="Имя Фамилия",
        is_leader=False,
        group_tg_id=12345
    )

    # Удаляем студента и проверяем сообщение
    msg = await delete_student(session, username="@student2")
    assert "удален" in msg

    # Повторная попытка удаления должна вернуть сообщение о ненахождении
    msg2 = await delete_student(session, username="@student25")
    assert "не найден" in msg2

@pytest.mark.asyncio
async def test_get_students_by_group(session):
    # Создаём группу
    group = Group(
        group_tg_id=777,
        group_name="Group 777",
        group_course=3,
        group_number=7,
        tg_link="link",
        schedule={}
    )
    session.add(group)
    await session.commit()
    await session.refresh(group)

    # Добавляем двух студентов
    await add_student(
        session,
        username="@stu1",
        full_name="Student1",
        is_leader=False,
        group_tg_id=777
    )

    await add_student(
        session,
        username="@stu2",
        full_name="Student2",
        is_leader=False,
        group_tg_id=777
    )

    students = await get_students_by_group(session, group_tg_id=777)
    assert len(students) == 2
    usernames = [s.student_username for s in students]
    assert "@stu1" in usernames and "@stu2" in usernames

@pytest.mark.asyncio
async def test_update_leader(session):
    # Готовим группу и студентов
    group = Group(
        group_tg_id=555,
        group_name="LeaderGroup",
        group_course=3,
        group_number=9,
        tg_link="link",
        schedule={}
    )
    session.add(group)
    await session.commit()
    await session.refresh(group)

    await add_student(
        session,
        username="@stuA",
        full_name="Student A",
        is_leader=False,
        group_tg_id=555
    )
    await add_student(
        session,
        username="@stuB",
        full_name="Student B",
        is_leader=True,
        group_tg_id=555
    )

    # Назначаем нового старосту
    msg = await update_leader(session, username="@stuA")
    assert "назначен старостой" in msg

    students = await get_students_by_group(session, group_tg_id=555)
    leader_count = sum(1 for s in students if s.student_is_leader)
    assert leader_count == 1
    assert any(s.student_username == "@stuA" and s.student_is_leader for s in students)

    # Для несуществующего
    msg2 = await update_leader(session, username="@nonexistent")
    assert "не найден" in msg2

@pytest.mark.asyncio
async def test_get_group_field(session):
    tg_id = 444
    await add_group(
        session,
        group_tg_id=tg_id,
        name="FieldTest",
        course=4,
        number=10,
        link="link",
        schedule={"Вторник": ["X"]}
    )
    # Существующее поле
    field_val = await get_group_field(session, group_tg_id=tg_id, field="schedule")
    assert field_val == {"Вторник": ["X"]}

    # Несуществующее поле
    assert await get_group_field(session, group_tg_id=tg_id, field="nonexistent") is None
    # Несуществующая группа
    assert await get_group_field(session, group_tg_id=9999, field="schedule") is None

@pytest.mark.asyncio
async def test_update_group_field(session):
    tg_id = 404
    await add_group(
        session,
        group_tg_id=tg_id,
        name="SomeGroup",
        course=1,
        number=1,
        link="link",
        schedule={"Среда": []},
    )

    # Обновляем события
    msg = await update_group_field(session, group_tg_id=tg_id, field="events", value={"Среда": "test"})
    assert "обновлено" in msg

    group = await get_group_by_tg_id(session, group_tg_id=tg_id)
    assert group.events == {"Среда": "test"}

    # Недопустимое поле
    msg_invalid = await update_group_field(session, group_tg_id=tg_id, field="qwe", value="x")
    assert "Недопустимое поле" in msg_invalid

    # Несуществующая группа
    msg_no_group = await update_group_field(session, group_tg_id=856, field="schedule", value={})
    assert "не найдена" in msg_no_group

@pytest.mark.asyncio
async def test_is_student_leader(session):
    # Готовим группу и студента
    group = Group(
        group_tg_id=2021,
        group_name="LeaderTest",
        group_course=5,
        group_number=10,
        tg_link="link",
        schedule={}
    )
    session.add(group)
    await session.commit()
    await session.refresh(group)

    # Добавляем студента без статуса старосты
    await add_student(
        session,
        username="@noLeader",
        full_name="No Leader",
        is_leader=False,
        group_tg_id=2021
    )

    # Проверяем, что студент не староста
    assert await is_student_leader(session, username="@noLeader") is False

    # Добавляем второго студента со статусом старосты
    await add_student(
        session,
        username="@yesLeader",
        full_name="Yes Leader",
        is_leader=True,
        group_tg_id=2021
    )

    # Проверяем, что студент староста
    assert await is_student_leader(session, username="@yesLeader") is True

    # Для несуществующего студента должно выбрасываться исключение
    with pytest.raises(ValueError):
        await is_student_leader(session, username="@ghost")
