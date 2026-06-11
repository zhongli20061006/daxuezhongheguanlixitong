"""
后勤报修接口
POST /repairs            — 创建报修
GET  /repairs            — 查看报修列表（按角色筛选）
PUT  /repairs/{id}/status — 更新报修状态（含流转规则校验）
"""
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.deps import get_current_user, require_role
from app.models.repair import Repair, RepairStatus, RepairType
from app.services.event_bus import Events, event_bus
from app.services.notification_service import notification_service
from app.schemas.repair import (
    RepairCreateRequest, RepairStatusUpdateRequest,
    RepairItem, RepairListResponse,
)

router = APIRouter(prefix="/repairs", tags=["后勤"])

# 状态流转规则：允许的 (当前状态 → 目标状态) 映射
STATUS_TRANSITIONS: dict[RepairStatus, list[RepairStatus]] = {
    RepairStatus.submitted: [RepairStatus.accepted, RepairStatus.cancelled],
    RepairStatus.accepted: [RepairStatus.processing, RepairStatus.cancelled],
    RepairStatus.processing: [RepairStatus.completed],
    RepairStatus.completed: [RepairStatus.confirmed],
    RepairStatus.confirmed: [],   # 终态
    RepairStatus.cancelled: [],   # 终态
}


@router.post("", status_code=201, summary="创建报修")
async def create_repair(
    req: RepairCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not req.location or not req.location.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="报修地点不能为空")
    if not req.description or not req.description.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="报修描述不能为空")

    try:
        repair = Repair(
            user_id=current_user["username"],
            role=current_user["role"],
            location=req.location.strip(),
            type=req.type,
            description=req.description.strip(),
            status=RepairStatus.submitted.value,
        )
        db.add(repair)
        await db.commit()
        await db.refresh(repair)
        return _to_repair_item(repair)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("", response_model=RepairListResponse, summary="查询报修列表")
async def list_repairs(
    status_filter: str | None = Query(None, alias="status", description="按状态筛选"),
    type_filter: str | None = Query(None, alias="type", description="按类型筛选"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    按角色返回报修列表：
    - 学生/教师：自己提交的报修
    - 后勤工人：分配给自己的报修
    - 管理员：全部
    """
    query = select(Repair)
    role = current_user["role"]

    if role in ("student", "teacher"):
        query = query.where(Repair.user_id == current_user["username"])
    elif role == "staff":
        query = query.where(Repair.assigned_worker_id == current_user["username"])
    elif role == "admin":
        pass  # 管理员看全部
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问")

    if status_filter:
        query = query.where(Repair.status == status_filter)
    if type_filter:
        query = query.where(Repair.type == type_filter)

    result = await db.execute(query.order_by(Repair.submit_time.desc()))
    repairs = result.scalars().all()
    return RepairListResponse(repairs=[_to_repair_item(r) for r in repairs])


@router.put("/{repair_id}/status", response_model=RepairItem, summary="更新报修状态")
async def update_repair_status(
    repair_id: int,
    req: RepairStatusUpdateRequest,
    current_user: dict = Depends(require_role("staff", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    更新报修状态，校验流转规则：
    提交→已接单/已取消 → 已接单→处理中/已取消 → 处理中→已完成 → 已完成→已确认
    终态（已确认、已取消）不可再变更
    同时更新对应的时间戳字段
    """
    result = await db.execute(select(Repair).where(Repair.id == repair_id))
    repair = result.scalar_one_or_none()
    if not repair:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报修记录不存在")

    current_status = RepairStatus(repair.status)
    new_status = RepairStatus(req.status)
    role = current_user["role"]
    worker_id = current_user["username"]

    # 校验状态流转规则
    allowed_next = STATUS_TRANSITIONS.get(current_status, [])
    if new_status not in allowed_next:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不允许从'{current_status.value}'变更为'{new_status.value}'",
        )

    # 后勤工人只能操作分配给自己的报修（管理员不受限）
    if role == "staff" and repair.assigned_worker_id and repair.assigned_worker_id != worker_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="只能操作分配给自己的报修"
        )

    # 更新状态 + 对应时间戳
    repair.status = new_status.value
    now = datetime.now()
    if new_status == RepairStatus.accepted:
        repair.accept_time = now
        if not repair.assigned_worker_id:
            repair.assigned_worker_id = worker_id
    elif new_status == RepairStatus.completed:
        repair.complete_time = now
    elif new_status == RepairStatus.confirmed:
        repair.confirm_time = now
    elif new_status == RepairStatus.cancelled:
        repair.cancel_time = now

    await db.commit()
    await db.refresh(repair)

    # 触发通知事件（在独立的db session中执行通知创建）
    async def _notify():
        async with AsyncSessionLocal() as s:
            await notification_service.create_notification(
                db=s,
                title="报修状态更新",
                content=f"报修单 #{repair.id} 状态变更为：{repair.status}，地点：{repair.location}",
                recipient_id=repair.user_id,
                event_type=Events.REPAIR_STATUS_CHANGED,
            )
            await s.commit()
    asyncio.create_task(_notify())

    return _to_repair_item(repair)


def _to_repair_item(r: Repair) -> RepairItem:
    """ORM对象 → Pydantic响应"""
    return RepairItem(
        id=r.id,
        user_id=r.user_id,
        role=r.role,
        location=r.location,
        type=r.type,
        description=r.description,
        status=r.status,
        assigned_worker_id=r.assigned_worker_id,
        submit_time=r.submit_time.strftime("%Y-%m-%d %H:%M:%S") if r.submit_time else "",
        accept_time=r.accept_time.strftime("%Y-%m-%d %H:%M:%S") if r.accept_time else None,
        complete_time=r.complete_time.strftime("%Y-%m-%d %H:%M:%S") if r.complete_time else None,
        confirm_time=r.confirm_time.strftime("%Y-%m-%d %H:%M:%S") if r.confirm_time else None,
        cancel_time=r.cancel_time.strftime("%Y-%m-%d %H:%M:%S") if r.cancel_time else None,
    )
