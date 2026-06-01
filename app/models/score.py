from __future__ import annotations

import enum
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, Numeric, DateTime, Enum as SAEnum, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ScoreType(str, enum.Enum):
    """成绩类型枚举"""
    daily = "平时"
    final = "期末"
    total = "总评"


class Score(Base):
    """
    成绩表
    存储学生的平时/期末/总评成绩和对应绩点
    唯一键 (student_id, schedule_id, score_type, attempt) 保证同一类型+同一尝试次数只有一条记录
    score 字段对于总评记录为 NULL（因为总评由平时+期末加权计算，不直接存储百分制分数）
    """
    __tablename__ = "score"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="成绩ID，自增")
    student_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("student.id"), nullable=False, comment="学号"
    )
    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("schedule.id"), nullable=False, comment="课表ID"
    )
    # Numeric(4,1): 精度4位、小数1位 → 范围 0.0~999.9，适用于百分制（0~100）
    score: Mapped[float | None] = mapped_column(
        Numeric(4, 1), nullable=True, comment="百分制分数，总评记录为NULL"
    )
    # Numeric(2,1): 精度2位、小数1位 → 范围 0.0~9.9，5分制绩点
    gpa: Mapped[float] = mapped_column(
        Numeric(2, 1), nullable=False, comment="绩点，5分制"
    )
    score_type: Mapped[ScoreType] = mapped_column(
        SAEnum(ScoreType), nullable=False, default=ScoreType.total,
        comment="成绩类型：平时/期末/总评"
    )
    attempt: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="考试次数：1=首次, 2=补考"
    )
    # onupdate=func.now(): 每次 UPDATE 行时自动更新此字段为当前时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, comment="最后更新时间"
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id", "schedule_id", "score_type", "attempt",
            name="uk_student_schedule_type_attempt",
        ),
    )
