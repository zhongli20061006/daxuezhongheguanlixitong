from __future__ import annotations

import enum
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class UserRole(str, enum.Enum):
    """用户角色枚举，映射到 MySQL ENUM 类型"""
    student = "student"
    teacher = "teacher"
    staff = "staff"
    admin = "admin"


class UserCredential(Base):
    """
    用户认证表
    统一管理四种角色的登录凭据：学生/教师/后勤/管理员
    role + role_id 联合定位具体角色表记录（无 FK 约束，因为指向不同表）
    """
    __tablename__ = "user_credential"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="用户ID，自增")
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="用户名=学号或工号"
    )
    # 密码通过 passlib 的 bcrypt 加密后存储，永不明文存放
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="bcrypt加密后的密码哈希")
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole), nullable=False, comment="角色：student/teacher/staff/admin"
    )
    # role_id 指向对应角色表的主键，如 student.id / teacher.job_number / staff.id
    role_id: Mapped[str] = mapped_column(String(20), nullable=False, comment="对应角色表的主键ID")
    # must_change_password=True → 前端检测到此标志时强制跳转修改密码页
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="首次登录是否必须修改密码"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, comment="账户创建时间"
    )

    __table_args__ = (
        Index("idx_username", "username"),
        Index("idx_role", "role", "role_id"),
    )
