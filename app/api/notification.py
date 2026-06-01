"""
通知接口
GET /notification/list            — 获取通知列表
GET /notification/unread-count    — 未读数量
POST /notification/{id}/read      — 标记已读
POST /notification/read-all       — 全部已读
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.schemas.notification import NotificationItem, NotificationListResponse, UnreadCountResponse
from app.services.notification_service import notification_service

router = APIRouter(prefix="/notification", tags=["通知"])


@router.get("/list", response_model=NotificationListResponse, summary="通知列表")
async def list_notifications(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    items = await notification_service.get_user_notifications(
        db, current_user["username"], current_user["role"], limit, offset
    )
    return NotificationListResponse(notifications=[
        NotificationItem(**item) for item in items
    ])


@router.get("/unread-count", response_model=UnreadCountResponse, summary="未读通知数")
async def unread_count(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await notification_service.get_unread_count(
        db, current_user["username"], current_user["role"]
    )
    return UnreadCountResponse(count=count)


@router.post("/{notification_id}/read", summary="标记已读")
async def mark_read(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await notification_service.mark_as_read(db, notification_id)
    return {"message": "已标记为已读"}


@router.post("/read-all", summary="全部已读")
async def read_all(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notifications = await notification_service.get_user_notifications(
        db, current_user["username"], current_user["role"], limit=200
    )
    for n in notifications:
        if not n["is_read"]:
            await notification_service.mark_as_read(db, n["id"])
    return {"message": "全部标记为已读"}
