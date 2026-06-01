from __future__ import annotations

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Student(Base):
    """学生表 — 学号作为主键，与 user_credential.role_id 对应"""
    __tablename__ = "student"

    id: Mapped[str] = mapped_column(String(20), primary_key=True, comment="学号作为主键，如S2024001")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="学生姓名")
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="手机号")
    id_card: Mapped[str | None] = mapped_column(String(18), nullable=True, comment="身份证号，18位")
    class_id: Mapped[int | None] = mapped_column(ForeignKey("class.id"), nullable=True, comment="所属班级ID")

    # 所属班级（多对一：多名学生属于一个班级）
    student_class: Mapped["StudentClass | None"] = relationship(back_populates="students")
