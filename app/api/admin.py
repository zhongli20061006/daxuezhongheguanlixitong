"""
管理端接口
POST /admin/selection-window           — 设置选课时间窗口
GET  /admin/selection-window           — 查询当前窗口配置
PUT  /admin/capacity/{schedule_id}     — 修改课程容量（窗口开启后禁止）
GET  /admin/users                      — 用户列表
POST /admin/reset-password/{user_id}   — 重置密码
"""
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.database import get_db
from app.deps import require_role
from app.models import (
    SystemConfig, CourseCapacity, Schedule, UserCredential,
)
from app.schemas.admin import (
    SelectionWindowRequest, SelectionWindowResponse,
    CapacityUpdateRequest, ResetPasswordRequest,
    UserItem, UserListResponse,
)

router = APIRouter(prefix="/admin", tags=["管理端"])


@router.post("/selection-window", summary="设置选课窗口")
async def set_selection_window(
    req: SelectionWindowRequest,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """管理员设置选课开始/结束时间和退课截止时间（UPSERT）"""
    # 校验时间一致性
    try:
        st = datetime.strptime(req.selection_start_time, "%Y-%m-%d %H:%M:%S") if req.selection_start_time else None
        et = datetime.strptime(req.selection_end_time, "%Y-%m-%d %H:%M:%S") if req.selection_end_time else None
        dd = datetime.strptime(req.drop_deadline, "%Y-%m-%d %H:%M:%S") if req.drop_deadline else None
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="时间格式错误，请使用 YYYY-MM-DD HH:MM:SS")
    if st and et and st >= et:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="选课开始时间必须早于结束时间")
    if st and dd and dd <= st:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="退课截止时间必须晚于选课开始时间")

    configs = {
        "selection_start_time": req.selection_start_time,
        "selection_end_time": req.selection_end_time,
        "drop_deadline": req.drop_deadline,
    }
    for key, val in configs.items():
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.config_key == key)
        )
        cfg = result.scalar_one_or_none()
        if cfg:
            cfg.config_value = val
        else:
            db.add(SystemConfig(config_key=key, config_value=val))

    await db.commit()
    return {"message": "选课时间窗口已设置"}


@router.get("/selection-window", response_model=SelectionWindowResponse, summary="查询选课窗口")
async def get_selection_window(
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """查询当前选课时间窗口配置"""
    result = await db.execute(select(SystemConfig))
    configs = {c.config_key: c.config_value for c in result.scalars().all()}
    return SelectionWindowResponse(
        selection_start_time=configs.get("selection_start_time"),
        selection_end_time=configs.get("selection_end_time"),
        drop_deadline=configs.get("drop_deadline"),
    )


@router.put("/capacity/{schedule_id}", summary="修改课程容量")
async def update_capacity(
    schedule_id: int,
    req: CapacityUpdateRequest,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    修改课程容量
    校验：选课窗口已开启时禁止修改（保护并发安全）
    """
    # 检查容量记录是否存在
    cap_result = await db.execute(
        select(CourseCapacity).where(CourseCapacity.schedule_id == schedule_id)
    )
    cap = cap_result.scalar_one_or_none()
    if not cap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程容量记录不存在")

    # 检查选课窗口是否已开启 → 已开启则禁止修改
    now = datetime.now()
    cfg_result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == "selection_start_time")
    )
    cfg = cfg_result.scalar_one_or_none()
    if cfg and cfg.config_value:
        try:
            start_time = datetime.strptime(cfg.config_value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="选课时间配置错误")
        if now >= start_time:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="选课窗口已开启，禁止修改课程容量",
            )

    cap.capacity = req.capacity
    await db.commit()
    return {"message": "课程容量已更新", "schedule_id": schedule_id, "capacity": req.capacity}


@router.get("/users", response_model=UserListResponse, summary="用户列表")
async def list_users(
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """管理员查看所有用户"""
    result = await db.execute(select(UserCredential))
    users = result.scalars().all()
    return UserListResponse(users=[
        UserItem(
            id=u.id,
            username=u.username,
            role=u.role.value,
            role_id=u.role_id,
            must_change_password=u.must_change_password,
            created_at=u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else "",
        )
        for u in users
    ])


@router.post("/reset-password/{user_id}", summary="重置密码")
async def reset_password(
    user_id: int,
    req: ResetPasswordRequest,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    管理员重置指定用户的密码
    密码重置后 must_change_password 置为 True，该用户下次登录必须修改密码
    """
    result = await db.execute(
        select(UserCredential).where(UserCredential.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    user.password_hash = bcrypt.hashpw(req.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user.must_change_password = True
    await db.commit()
    return {"message": f"用户 {user.username} 的密码已重置"}
