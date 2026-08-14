from pydantic_settings import BaseSettings
from pydantic import field_validator

# 已知的示例占位密钥前缀：绝不接受这些值（fail-closed）
WEAK_SECRET_KEY_PREFIXES = (
    "change-me-in-production",
    "your-secret-key-change-in-production",
)


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
    # ===== 智能体助手配置 =====
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_timeout: float = 10.0
    ollama_max_concurrency: int = 4
    ollama_queue_timeout: float = 15.0
    ollama_circuit_failures: int = 3
    ollama_circuit_cooldown: float = 60.0
    agent_confirm_ttl: int = 300
    agent_session_ttl: int = 1800
    agent_session_limit: int = 20
    context_budget_tokens: int = 8000

    @field_validator("secret_key")
    @classmethod
    def _validate_secret_key(cls, v: str) -> str:
        v = (v or "").strip()
        if len(v) < 32:
            raise ValueError(
                "SECRET_KEY 长度须不少于 32 字符；"
                '生成方式：python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        if v.startswith(WEAK_SECRET_KEY_PREFIXES):
            raise ValueError("SECRET_KEY 不能使用示例占位值，请注入随机密钥")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
