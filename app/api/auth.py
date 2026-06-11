"""
认证接口
POST /auth/login     — 登录获取 JWT token（每分钟限 5 次 / IP）
POST /auth/change-password — 修改密码（需登录）
POST /auth/logout    — 清除认证 cookie
"""
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import UserCredential
from app.deps import create_access_token, get_current_user
from app.schemas.auth import LoginRequest, ChangePasswordRequest
from app.main import limiter

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", summary="用户登录")
@limiter.limit("5/minute")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db), request: Request = None):
    """
    验证用户名密码，通过 httpOnly cookie 下发 JWT token
    同时返回 token 体用于 WebSocket 连接（WS 无法携带 cookie）
    如果 must_change_password=True，前端应强制跳转修改密码页面
    """
    result = await db.execute(
        select(UserCredential).where(UserCredential.username == req.username)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
        )
    if not bcrypt.checkpw(req.password.encode('utf-8'), user.password_hash.encode('utf-8')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
        )

    token = create_access_token(
        username=user.username,
        role=user.role.value,
        role_id=user.role_id,
    )
    response = JSONResponse(content={
        "access_token": token,
        "role": user.role.value,
        "must_change_password": user.must_change_password,
    })
    # 设置 httpOnly cookie（JS 不可读，防 XSS 窃取）
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="strict",
        secure=False,  # 生产环境应设为 True（HTTPS）
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    return response


@router.post("/logout", summary="退出登录")
async def logout():
    """清除认证 cookie"""
    response = JSONResponse(content={"message": "已退出登录"})
    response.delete_cookie(key="access_token", path="/")
    return response


@router.get("/me", summary="获取当前用户信息")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    从 cookie 中解析 JWT，返回当前用户信息
    前端用它替代 localStorage 判断登录态
    """
    result = await db.execute(
        select(UserCredential).where(UserCredential.username == current_user["username"])
    )
    user = result.scalar_one_or_none()
    return {
        "username": current_user["username"],
        "role": current_user["role"],
        "must_change_password": user.must_change_password if user else False,
    }


@router.post("/change-password", summary="修改密码")
async def change_password(
    req: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    验证旧密码后更新为新密码，并关闭首次登录强制修改标记
    """
    result = await db.execute(
        select(UserCredential).where(UserCredential.username == current_user["username"])
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在"
        )

    if req.old_password == req.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能与旧密码相同"
        )

    if not bcrypt.checkpw(req.old_password.encode('utf-8'), user.password_hash.encode('utf-8')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码不正确"
        )

    user.password_hash = bcrypt.hashpw(req.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user.must_change_password = False
    await db.commit()

    return {"message": "密码修改成功"}
