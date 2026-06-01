"""
通知服务
处理通知的创建、持久化和 WebSocket 实时推送
"""
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationUser
from app.services.websocket_manager import ws_manager


class NotificationService:

    async def create_notification(
        self,
        db: AsyncSession,
        title: str,
        content: str,
        recipient_role: str | None = None,
        recipient_id: str | None = None,
        event_type: str | None = None,
    ) -> Notification:
        notification = Notification(
            title=title,
            content=content,
            event_type=event_type,
            created_at=datetime.now(),
        )
        db.add(notification)
        await db.flush()

        nu = NotificationUser(
            notification_id=notification.id,
            recipient_role=recipient_role,
            recipient_id=recipient_id,
            is_read=False,
        )
        db.add(nu)

        if recipient_id:
            await ws_manager.send(recipient_id, {
                "type": "notification",
                "data": {
                    "id": notification.id,
                    "title": title,
                    "content": content,
                    "created_at": notification.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "is_read": False,
                }
            })

        return notification

    async def get_user_notifications(
        self,
        db: AsyncSession,
        user_id: str,
        role: str,
        limit: int = 50,
        offset: int = 0,
    ):
        result = await db.execute(
            select(Notification, NotificationUser)
            .join(NotificationUser, Notification.id == NotificationUser.notification_id)
            .where(
                (NotificationUser.recipient_id == user_id) |
                (NotificationUser.recipient_role == role) |
                ((NotificationUser.recipient_id.is_(None)) & (NotificationUser.recipient_role.is_(None)))
            )
            .order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = result.all()
        notifications = []
        for notif, nu in rows:
            notifications.append({
                "id": notif.id,
                "title": notif.title,
                "content": notif.content,
                "event_type": notif.event_type,
                "created_at": notif.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "is_read": nu.is_read,
            })
        return notifications

    async def mark_as_read(self, db: AsyncSession, notification_id: int):
        await db.execute(
            update(NotificationUser)
            .where(NotificationUser.notification_id == notification_id)
            .values(is_read=True)
        )

    async def get_unread_count(
        self,
        db: AsyncSession,
        user_id: str,
        role: str,
    ) -> int:
        result = await db.execute(
            select(NotificationUser)
            .join(Notification, Notification.id == NotificationUser.notification_id)
            .where(
                NotificationUser.is_read == False,
                (NotificationUser.recipient_id == user_id) |
                (NotificationUser.recipient_role == role) |
                ((NotificationUser.recipient_id.is_(None)) & (NotificationUser.recipient_role.is_(None)))
            )
        )
        return len(result.scalars().all())


notification_service = NotificationService()
