from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置，自动从.env文件和系统环境变量加载参数"""
    # 异步URL：FastAPI路由依赖注入使用（create_async_engine）
    database_url: str = "mysql+aiomysql://root:password@localhost:3306/student_management"
    # 同步URL：初始化脚本使用（create_engine），避免脚本中写asyncio.run()
    sync_database_url: str = "mysql+pymysql://root:password@localhost:3306/student_management"
    # JWT认证参数 — SECRET_KEY 强制通过 .env 注入，无默认值
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    # CORS — 允许的前端来源（逗号分隔），开发环境可用 *
    allowed_origins: str = "http://localhost:5175"
    # SQL调试 — 开发环境开启回显，生产环境务必关闭
    debug_sql: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
