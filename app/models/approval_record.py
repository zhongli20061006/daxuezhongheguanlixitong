"""
审批记录表
记录请假申请的每一级审批流转
"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ApprovalRecord(Base):
    __tablename__ = "approval_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="审批ID")
    leave_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="请假申请ID")
    approver_id: Mapped[str] = mapped_column(String(20), nullable=False, comment="审批人工号")
    approver_role: Mapped[str] = mapped_column(String(20), nullable=False, comment="审批人角色：advisor/college")
    level: Mapped[int] = mapped_column(Integer, nullable=False, comment="审批级别：1=辅导员 2=学院")
    result: Mapped[str] = mapped_column(String(20), nullable=False, comment="审批结果：通过/驳回")
    comment: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审批意见")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="审批时间"
    )

    # 同一请假单同一审批级别唯一：防止并发/重复审批（幂等防护）
    __table_args__ = (
        UniqueConstraint("leave_id", "level", name="uk_leave_level"),
    )
