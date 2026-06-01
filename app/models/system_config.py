from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SystemConfig(Base):
    """
    系统配置表 — 键值对存储运行时参数
    初始化时写入选课窗口时间、退课截止时间等配置
    通过 config_key 查询对应值，无需 JOIN
    """
    __tablename__ = "system_config"

    config_key: Mapped[str] = mapped_column(String(50), primary_key=True, comment="配置键")
    config_value: Mapped[str] = mapped_column(String(255), nullable=False, comment="配置值")
    # onupdate=func.now(): 每次更新值时自动刷新时间戳
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, comment="最后更新时间"
    )
