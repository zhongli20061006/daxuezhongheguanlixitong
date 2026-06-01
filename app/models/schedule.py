from __future__ import annotations

from sqlalchemy import String, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Schedule(Base):
    """
    课表基础表
    不存具体日期，改为存周次+星期几+节次，避免每年的日期变动导致数据失效
    """
    __tablename__ = "schedule"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="课表ID，自增")
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teacher.id"), nullable=False, comment="授课教师工号")
    subject_id: Mapped[int] = mapped_column(ForeignKey("subject.id"), nullable=False, comment="科目ID")
    class_id: Mapped[int] = mapped_column(ForeignKey("class.id"), nullable=False, comment="授课班级ID")
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classroom.id"), nullable=False, comment="教室ID")
    weeks: Mapped[str] = mapped_column(String(20), nullable=False, comment="上课周次，如1-18或1-18(单)")
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False, comment="星期几，1=周一，7=周日")
    period: Mapped[str] = mapped_column(String(10), nullable=False, comment="节次，如1-2表示第1-2节")
    semester: Mapped[str] = mapped_column(String(20), nullable=False, comment="学期，如2024-2025-1")

    # 关系定义 — back_populates 实现双向导航
    teacher: Mapped["Teacher"] = relationship(back_populates="schedules")
    subject: Mapped["Subject"] = relationship(back_populates="schedules")
    student_class: Mapped["StudentClass"] = relationship(back_populates="schedules")
    classroom: Mapped["Classroom"] = relationship(back_populates="schedules")

    # 一对一：课表对应一条容量记录（限选/选修课才有）
    course_capacity: Mapped["CourseCapacity | None"] = relationship(back_populates="schedule")
    # 一对多：课表可被多名学生选课
    selections: Mapped[list["CourseSelection"]] = relationship(back_populates="schedule")

    # 复合索引：覆盖按班级/教师/教室查询课表的常见场景
    __table_args__ = (
        Index("idx_class_semester", "class_id", "semester"),
        Index("idx_teacher_semester", "teacher_id", "semester"),
        Index("idx_classroom_semester", "classroom_id", "semester"),
    )
