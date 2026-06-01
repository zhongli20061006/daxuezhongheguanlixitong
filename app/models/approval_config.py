"""
审批配置表
定义不同请假时长需要经过的审批级别
"""
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ApprovalConfig(Base):
    __tablename__ = "approval_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="配置ID")
    min_days: Mapped[int] = mapped_column(Integer, nullable=False, comment="最小天数(含)")
    max_days: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="最大天数(含)，NULL表示无上限")
    required_levels: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="需要审批的级别，逗号分隔：1,2"
    )
