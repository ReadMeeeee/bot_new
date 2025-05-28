import pytest, os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from bot_api.Database.models import Base


TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_db.sqlite3"


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
    db_path = TEST_DATABASE_URL.split(":///")[-1]
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture(scope="session")
async def session(test_engine):
    async_session = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
