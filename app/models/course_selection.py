from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class CourseSelection(Base):
    """
    选课记录表

    设计要点：唯一键 (student_id, schedule_id, status) 确保：
    - 每个学生+课程最多一条 status=1 记录（已选）
    - 每个学生+课程最多一条 status=0 记录（已退，保留历史）
    选课→退课→重新选课 的操作流程：
      选课: 尝试 UPDATE status=0 → 1（有退课记录时），或 INSERT 新行（首次选课）
      退课: UPDATE status=1 → 0 并记录 cancel_time
    这样实现了“保留历史又不产生重复有效记录”的效果
    """
    __tablename__ = "course_selection"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="记录ID，自增")
    student_id: Mapped[str] = mapped_column(String(20), nullable=False, comment="学号，对应 student.id")
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedule.id"), nullable=False, comment="课表ID")
    # server_default=func.now(): 时间由数据库服务器生成，避免多应用服务器时间不一致
    select_time: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="选课时间"
    )
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="1=已选(有效), 0=已退(历史记录)")
    cancel_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="退课时间")

    schedule: Mapped["Schedule"] = relationship(back_populates="selections")

    __table_args__ = (
        UniqueConstraint("student_id", "schedule_id", "status", name="uk_student_schedule"),
        Index("idx_student_status", "student_id", "status"),
        Index("idx_schedule_status", "schedule_id", "status"),
    )
