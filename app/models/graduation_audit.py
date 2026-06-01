"""
毕业审核表
存储每个学生的毕业审核结果
"""
from datetime import datetime
from sqlalchemy import String, Integer, Numeric, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class GraduationAudit(Base):
    __tablename__ = "graduation_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="审核ID")
    student_id: Mapped[str] = mapped_column(String(20), nullable=False, comment="学号")
    plan_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="培养方案ID")
    total_credits_earned: Mapped[float] = mapped_column(
        Numeric(5, 1), nullable=False, default=0, comment="已获得总学分"
    )
    elective_credits_earned: Mapped[float] = mapped_column(
        Numeric(5, 1), nullable=False, default=0, comment="已获得选修学分"
    )
    compulsory_passed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="必修课通过门数"
    )
    compulsory_total: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="必修课总门数"
    )
    limited_groups_passed: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="限选各组满足情况JSON"
    )
    is_graduatable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否满足毕业条件"
    )
    detail: Mapped[str | None] = mapped_column(
        String(2000), nullable=True, comment="审核详情"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
