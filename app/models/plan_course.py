"""
培养方案课程明细表
定义培养方案中每门课的要求（必修必须通过，限选每组至少选min_required门）
"""
from sqlalchemy import String, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class PlanCourse(Base):
    __tablename__ = "plan_course"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="明细ID")
    plan_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="方案ID"
    )
    subject_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="科目ID"
    )
    course_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="课程类型：compulsory/limited/elective"
    )
    limited_group: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="限选组名，仅limited类型课程使用"
    )
    min_required: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="限选组至少选课门数，仅limited课程使用"
    )
    credit: Mapped[float] = mapped_column(
        Numeric(4, 1), nullable=False, comment="课程学分"
    )
