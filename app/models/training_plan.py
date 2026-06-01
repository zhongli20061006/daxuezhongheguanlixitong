"""
培养方案主表
定义各专业+年级的毕业要求
"""
from sqlalchemy import String, Integer, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class TrainingPlan(Base):
    __tablename__ = "training_plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="方案ID")
    major: Mapped[str] = mapped_column(String(100), nullable=False, comment="专业名称")
    grade: Mapped[int] = mapped_column(Integer, nullable=False, comment="入学年级")
    total_credits_required: Mapped[float] = mapped_column(
        Numeric(5, 1), nullable=False, comment="总学分要求"
    )
    elective_credits_required: Mapped[float] = mapped_column(
        Numeric(5, 1), nullable=False, comment="选修课学分要求"
    )
