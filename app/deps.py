"""
认证依赖模块
提供 JWT 令牌生成/解析、get_current_user 依赖注入、角色校验中间件
兼容两种 token 携带方式：httpOnly cookie（主选）和 Authorization Header（回退）
"""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status, Cookie, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.config import settings

# 从 Authorization Header 提取 Bearer Token 的 FastAPI 安全方案（回退方案）
security_scheme = HTTPBearer(auto_error=False)


def create_access_token(username: str, role: str, role_id: str) -> str:
    """
    创建 JWT access token
    参数: username — 用户名（学号或工号）
          role — 角色 (student/teacher/staff/admin)
          role_id — 角色表主键ID，用于定位具体教师/学生记录
    返回: JWT 字符串，包含 sub/role/role_id/exp 字段
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": username,
        "role": role,
        "role_id": role_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    """
    解析并验证 JWT token
    参数: token — cookie 或 Authorization Header 中提取的 token
    返回: payload 字典 {"sub", "role", "role_id", "exp"}
    异常: HTTPException 401 — token 过期或被篡改
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证，请重新登录",
        )


async def get_current_user(
    request: Request,
    access_token: Annotated[str | None, Cookie()] = None,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)] = None,
) -> dict:
    """
    FastAPI 依赖注入：优先从 httpOnly cookie 读取 JWT，回退到 Authorization Header
    使用方法：user = Depends(get_current_user)
    返回: {"username": str, "role": str, "role_id": str}
    异常: 401 — 未提供 token 或 token 无效
    """
    token = access_token or (credentials.credentials if credentials else None)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭证，请先登录",
        )
    payload = decode_access_token(token)
    username = payload.get("sub")
    role = payload.get("role")
    role_id = payload.get("role_id")
    if not username or not role or not role_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证，请重新登录",
        )
    return {
        "username": username,
        "role": role,
        "role_id": role_id,
    }


def require_role(*allowed_roles: str):
    """
    角色校验依赖工厂：生成一个检查当前用户角色的依赖函数
    用法: user = Depends(require_role("student"))
          user = Depends(require_role("admin", "teacher"))
    参数: allowed_roles — 允许访问的角色列表
    返回: 依赖函数，校验通过时返回当前用户 dict
    异常: 403 — 角色不在允许列表中
    """
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要 {'/'.join(allowed_roles)} 角色",
            )
        return current_user
    return role_checker
