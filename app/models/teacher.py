from __future__ import annotations

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Teacher(Base):
    """教师表 — 工号为主键（非自增），与 user_credential.role_id 对应"""
    __tablename__ = "teacher"

    id: Mapped[int] = mapped_column(primary_key=True, comment="工号作为主键")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="教师姓名")
    job_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, comment="工号，唯一索引")
    department: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="所属院系")
    title: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="职称，如教授/副教授/讲师")
    is_college_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否为学院管理员")

    # 一个教师可授课多条课表记录
    schedules: Mapped[list["Schedule"]] = relationship(back_populates="teacher")
