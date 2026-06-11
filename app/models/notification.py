"""
通知模板表
存储系统自动生成的通知消息
"""
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Notification(Base):
    __tablename__ = "notification"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="通知ID")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="通知标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="通知正文")
    event_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="触发事件类型")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="创建时间"
    )


class NotificationUser(Base):
    __tablename__ = "notification_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    notification_id: Mapped[int] = mapped_column(ForeignKey("notification.id"), nullable=False, comment="通知ID")
    recipient_role: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="接收角色，NULL表示全局")
    recipient_id: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="接收人ID，NULL表示角色级别通知")
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否已读")
