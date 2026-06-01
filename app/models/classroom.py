from __future__ import annotations

from sqlalchemy import String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Classroom(Base):
    """教室表 — 存储教室基本信息和硬件设施"""
    __tablename__ = "classroom"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="教室ID，自增")
    name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="教室名称，如D201/实验楼A301"
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, comment="容纳人数")
    building: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="教学楼名称")
    has_projector: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否有投影仪")

    # 一个教室可有多条课表记录（不同时间不同课程）
    schedules: Mapped[list["Schedule"]] = relationship(back_populates="classroom")
