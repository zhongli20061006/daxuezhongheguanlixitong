from __future__ import annotations

import enum
from sqlalchemy import String, Numeric, Enum as SAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class SubjectType(str, enum.Enum):
    """
    科目类型枚举
    compulsory: 必修课 — 不进入选课系统，按班级自动分配
    limited:    限选课 — 学生需在指定分组内选择，需校验同组已选门数
    elective:   选修课 — 先到先得，满额即止
    """
    compulsory = "compulsory"
    limited = "limited"
    elective = "elective"


class Subject(Base):
    __tablename__ = "subject"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="科目ID，自增")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="科目名称")
    # Numeric(2, 1): 总精度2位，小数点后1位 → 范围 0.0~9.9
    credit: Mapped[float] = mapped_column(Numeric(2, 1), nullable=False, comment="学分")
    # SAEnum 映射到 MySQL 原生 ENUM 类型，数据完整性由数据库保证
    type: Mapped[SubjectType] = mapped_column(
        SAEnum(SubjectType), nullable=False,
        comment="必修(compulsory)/限选(limited)/选修(elective)"
    )
    # 限选课分组ID：同一分组内课程共享容量策略，仅 type=limited 时有值
    limited_group: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="限选课组ID，如CS_2024_LTD_01"
    )

    schedules: Mapped[list["Schedule"]] = relationship(back_populates="subject")

    __table_args__ = (
        Index("idx_type", "type"),
        Index("idx_limited_group", "limited_group"),
    )
