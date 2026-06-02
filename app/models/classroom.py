from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Classroom(Base):
    __tablename__ = "classroom"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="教室ID，自增")
    name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="教室名称，如D201/实验楼A301"
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, comment="容纳人数")
    building: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="教学楼名称")
    has_projector: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否有投影仪")
    type: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default="普通教室", comment="教室类型：普通教室/机房/实验室/阶梯教室"
    )

    schedules: Mapped[list["Schedule"]] = relationship(back_populates="classroom")


class ClassroomReservation(Base):
    __tablename__ = "classroom_reservation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="预约ID")
    classroom_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="教室ID")
    week: Mapped[int] = mapped_column(Integer, nullable=False, comment="教学周")
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False, comment="星期几")
    period: Mapped[str] = mapped_column(String(10), nullable=False, comment="节次，如1-2")
    user_id: Mapped[str] = mapped_column(String(20), nullable=False, comment="预约人学号/工号")
    user_role: Mapped[str] = mapped_column(String(10), nullable=False, comment="预约人角色")
    reason: Mapped[str] = mapped_column(String(200), nullable=False, comment="预约理由")
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="已预约", comment="已预约/已取消")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )
