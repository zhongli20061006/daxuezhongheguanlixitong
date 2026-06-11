"""
请假申请表
"""
import enum
from datetime import datetime, date
from sqlalchemy import String, Integer, Date, Text, DateTime, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class LeaveStatus(str, enum.Enum):
    """请假状态枚举"""
    PENDING_COUNSELOR = "审批中(辅导员)"
    PENDING_COLLEGE = "审批中(学院)"
    APPROVED = "已通过"
    REJECTED = "已驳回"
    CANCELLED = "已撤销"


class LeaveApplication(Base):
    __tablename__ = "leave_application"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="请假ID")
    student_id: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="学号"
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False, comment="开始日期")
    end_date: Mapped[date] = mapped_column(Date, nullable=False, comment="结束日期")
    total_days: Mapped[int] = mapped_column(Integer, nullable=False, comment="请假天数")
    reason: Mapped[str] = mapped_column(Text, nullable=False, comment="请假原因")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=LeaveStatus.PENDING_COUNSELOR.value,
        comment="状态：审批中(辅导员)/审批中(学院)/已通过/已驳回/已撤销"
    )
    submit_time: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="提交时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
