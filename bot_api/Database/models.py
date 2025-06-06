from sqlalchemy import BigInteger, String, Boolean, ForeignKey, Integer, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine


# Создание асинхронного движка базы данных
engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3', echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    """
    Базовый класс для всех ORM-моделей с поддержкой асинхронных атрибутов.
    """
    pass


# Таблица групп
class Group(Base):
    """
    Модель группы студентов.

    Поля:
        id (int): Суррогатный ключ группы.
        group_tg_id (int): Уникальный Telegram ID группы.
        tg_link (str): Ссылка на группу в Telegram.
        group_name (str): Полное название группы.
        group_course (int): Курс, на котором находится группа.
        group_number (int): Номер группы.
        events (dict): JSON с описанием предстоящих событий, загружаемых старостой.
        schedule (dict): JSON с полным расписанием группы по дням.
        homework (dict): JSON со списком домашних заданий для группы.

    Связи:
        students: список объектов Student, принадлежащих группе.
    """
    __tablename__ = 'groups'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)              # Суррогатный ID группы в БД

    group_tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)   # Телеграм ID группы
    tg_link: Mapped[str] = mapped_column(String, nullable=False)                        # Ссылка на группу в Telegram

    group_name: Mapped[str] = mapped_column(String, nullable=False)     # Название группы
    group_course: Mapped[int] = mapped_column(Integer, nullable=False)  # Курс группы
    group_number: Mapped[int] = mapped_column(Integer, nullable=False)  # Номер группы

    # news: Mapped[dict] = mapped_column(JSON, nullable=True) # Строка с последними новостями (актуальными (а как?))
                                                              # Проблема с ежедневным обновлением новостей и
                                                              # неактуальностью новостей в студенческих массах
                                                              # Возможно в будущем сделать отдельную таблицу News

    events: Mapped[dict] = mapped_column(JSON, nullable=True)      # Строка с событиями (староста кидает)
    schedule: Mapped[dict] = mapped_column(JSON, nullable=True)    # Строка с расписанием группы
    homework: Mapped[dict] = mapped_column(JSON, nullable=True)    # Строка с ДЗ группы

    students = relationship("Student", back_populates="group", cascade="all, delete-orphan")  # Связь с таблицей студентов


# Таблица студентов
class Student(Base):

    __tablename__ = 'students'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)

    student_username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    student_full_name: Mapped[str] = mapped_column(String, nullable=False)
    student_is_leader: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    group = relationship("Group", back_populates="students")


class homework(Base):
    __tablename__ = 'homeworks'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)

    subject: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    homework_data: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    expiration_date: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    group = relationship("Group", back_populates="homeworks")



'''
# Таблица личных заданий (на будущее)
class StudentTask(Base):
    __tablename__ = 'student_tasks'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True) # Суррогатный ID задания

    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)    # Внешний ключ на студента

    task: Mapped[str] = mapped_column(String, nullable=False)             # Задание
    is_done: Mapped[bool] = mapped_column(Boolean, default=False)         # Статус выполнения задания

    student = relationship("Student", back_populates="tasks")     # Связь с таблицей студента

# Таблица событий (на будущее)
class Events(Base):
    __tablename__ = 'events'
    group = relationship("Group", back_populates="events")

# Таблица расписания (на будущее)
class Schedule(Base):
    __tablename__ = 'schedules'
    group = relationship("Group", back_populates="schedules")

# Автообновляемая таблица новостей (на будущее)
'''
