from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Staff(Base):
    """后勤工人表 — 管理维修/清洁/餐饮等后勤人员"""
    __tablename__ = "staff"

    id: Mapped[str] = mapped_column(String(20), primary_key=True, comment="工号作为主键")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="员工姓名")
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="手机号")
    department: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="所属部门")
    job_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="工种：维修/清洁/餐饮等")
