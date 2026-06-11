from __future__ import annotations

import enum
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class RepairStatus(str, enum.Enum):
    """
    报修状态枚举及流转规则：
    提交 → 已接单 / 已取消
    已接单 → 处理中 / 已取消
    处理中 → 已完成
    已完成 → 已确认
    已取消 → 终态，不可变更
    已确认 → 终态，不可变更
    """
    submitted = "提交"
    accepted = "已接单"
    processing = "处理中"
    completed = "已完成"
    confirmed = "已确认"
    cancelled = "已取消"


class RepairType(str, enum.Enum):
    """报修类型枚举"""
    electrical = "水电设备"
    electronic = "电子产品"
    furniture = "家具类"
    teaching = "教学用具"


class Repair(Base):
    __tablename__ = "repair"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="报修ID，自增")
    # user_id 存学号或工号，role 区分身份。无 FK 约束（指向 student/teacher/staff 不同表）
    user_id: Mapped[str] = mapped_column(String(20), nullable=False, comment="报修人学号或工号")
    role: Mapped[str] = mapped_column(String(10), nullable=False, comment="报修人角色：student/teacher/staff")
    location: Mapped[str] = mapped_column(String(200), nullable=False, comment="报修地点")
    type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="报修类型：水电设备/电子产品/家具类/教学用具"
    )
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="问题详细描述")
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=RepairStatus.submitted.value, comment="当前状态"
    )
    # assigned_worker_id: 被分配处理的后勤工人工号（staff.id）
    assigned_worker_id: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="分配的后勤工人工号"
    )
    # 各状态的时间戳，到达对应状态时写入
    submit_time: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="提交时间"
    )
    accept_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="接单时间")
    complete_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="完成时间")
    confirm_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="确认时间")
    cancel_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="取消时间")

    __table_args__ = (
        Index("idx_user", "user_id"),
        Index("idx_status", "status"),
        Index("idx_worker", "assigned_worker_id"),
    )
