from __future__ import annotations

from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class StudentClass(Base):
    """
    班级表
    注意：Python 中 class 是关键字，不能用作类名和模块名
    故文件名为 student_class.py，类名为 StudentClass，__tablename__ 仍是 "class"
    """
    __tablename__ = "class"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="班级ID，自增")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="班级全称，如：2024级计算机科学1班")
    major: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="专业名称")
    grade: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="入学年份，如2024")
    advisor_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="辅导员工号，外键关联teacher.id")

    # 一个班级包含多名学生
    students: Mapped[list["Student"]] = relationship(back_populates="student_class")
    # 一个班级有多条课表记录
    schedules: Mapped[list["Schedule"]] = relationship(back_populates="student_class")
