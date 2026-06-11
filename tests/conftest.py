"""
Pytest 配置和共享 fixtures
定义测试数据库、HTTP 客户端、测试数据等
"""
import os
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# 强制测试环境配置
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("DEBUG_SQL", "false")

from app.config import settings
from app.database import Base
from app.main import app

# 测试数据库 URL（使用 SQLite 内存数据库以加速测试）
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """会话级测试引擎"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
    # 清理测试数据库文件
    if os.path.exists("test.db"):
        os.remove("test.db")


@pytest_asyncio.fixture
async def db(test_engine):
    """每个测试函数独立的数据库会话（自动回滚）"""
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db):
    """HTTP 测试客户端（注入测试数据库依赖）"""
    async def override_get_db():
        yield db

    app.dependency_overrides = {}
    from app.database import get_db
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
