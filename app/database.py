"""
数据库引擎和会话管理
提供两套引擎以满足不同场景：
- 异步引擎 (async_engine)：FastAPI 路由使用，支持高并发请求
- 同步引擎 (sync_engine)：命令行脚本使用，代码更简洁
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

# ===== 异步引擎 =====
# pool_size: 连接池最小连接数，max_overflow: 超过pool_size时可额外创建的连接数
# echo=True: 打印所有SQL语句，方便调试（生产环境改为False）
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug_sql,
    pool_size=10,
    max_overflow=20,
)
# expire_on_commit=False: 提交后对象不过期，避免在视图层访问已提交对象时触发延迟加载
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ===== 同步引擎 =====
sync_engine = create_engine(
    settings.sync_database_url,
    echo=settings.debug_sql,
)
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)


class Base(DeclarativeBase):
    """所有 ORM Model 的基类，Model 必须继承此类才能被 Base.metadata 管理"""
    pass


async def get_db():
    """
    FastAPI 依赖注入：为每个 HTTP 请求提供独立的异步数据库会话
    返回值: AsyncSession — 请求处理期间有效的异步会话对象
    用法:   db: AsyncSession = Depends(get_db)
    会话在请求结束后自动关闭（由 finally 块保证）
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
