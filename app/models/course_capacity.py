from __future__ import annotations

from sqlalchemy import Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class CourseCapacity(Base):
    """
    课程容量表 — 与 schedule 一对一，仅在选课系统中使用
    并发控制核心：通过原子 UPDATE course_capacity SET enrolled = enrolled + 1
    WHERE schedule_id = :id AND enrolled < capacity 实现无锁选课
    必修课不在此表中有记录（不进入选课流程）
    """
    __tablename__ = "course_capacity"

    # schedule_id 既是主键又是外键 → 每门课最多一条容量记录
    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("schedule.id"), primary_key=True, comment="关联课表ID"
    )
    # enrolled: 当前已选人数，由选课/退课 API 原子更新
    enrolled: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="已选人数")
    # capacity: 课程容量上限，选课窗口开启后禁止修改（业务规则保证）
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, comment="课程容量上限")

    schedule: Mapped["Schedule"] = relationship(back_populates="course_capacity")

    # 索引：加速 "SELECT ... WHERE enrolled < capacity" 的并发读取
    __table_args__ = (
        Index("idx_schedule_capacity", "schedule_id", "enrolled", "capacity"),
    )
