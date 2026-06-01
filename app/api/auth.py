"""
认证接口
POST /auth/login     — 登录获取 JWT token
POST /auth/change-password — 修改密码（需登录）
"""
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import UserCredential
from app.deps import create_access_token, get_current_user
from app.schemas.auth import LoginRequest, LoginResponse, ChangePasswordRequest

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=LoginResponse, summary="用户登录")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    验证用户名密码，返回 JWT token
    如果 must_change_password=True，前端应强制跳转修改密码页面
    """
    # 查询用户凭据（不区分大小写？用精确匹配）
    result = await db.execute(
        select(UserCredential).where(UserCredential.username == req.username)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
        )
    # 验证 bcrypt 哈希
    if not bcrypt.checkpw(req.password.encode('utf-8'), user.password_hash.encode('utf-8')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
        )

    # 生成 JWT，payload 包含用户名/角色/角色ID
    token = create_access_token(
        username=user.username,
        role=user.role.value,
        role_id=user.role_id,
    )
    return LoginResponse(
        access_token=token,
        role=user.role.value,
        must_change_password=user.must_change_password,
    )


@router.post("/change-password", summary="修改密码")
async def change_password(
    req: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    验证旧密码后更新为新密码，并关闭首次登录强制修改标记
    需在 Authorization Header 中传入 Bearer token
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

    # 验证旧密码
    if not bcrypt.checkpw(req.old_password.encode('utf-8'), user.password_hash.encode('utf-8')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码不正确"
        )

    # 更新密码哈希并清除强制修改标记
    user.password_hash = bcrypt.hashpw(req.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user.must_change_password = False
    await db.commit()

    return {"message": "密码修改成功"}
