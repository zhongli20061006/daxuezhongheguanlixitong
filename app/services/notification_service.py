"""
通知服务
处理通知的创建、持久化和 WebSocket 实时推送
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationUser
from app.services.websocket_manager import ws_manager

logger = logging.getLogger("student_management")


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

    async def mark_all_as_read(self, db: AsyncSession, user_id: str, role: str) -> int:
        """批量标记该用户所有未读通知为已读，返回影响行数"""
        result = await db.execute(
            update(NotificationUser)
            .where(
                NotificationUser.is_read == False,
                or_(
                    NotificationUser.recipient_id == user_id,
                    NotificationUser.recipient_role == role,
                    and_(NotificationUser.recipient_id.is_(None), NotificationUser.recipient_role.is_(None)),
                )
            )
            .values(is_read=True)
        )
        return result.rowcount

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

    async def delete_notification(self, db: AsyncSession, notification_id: int, user_id: str) -> bool:
        """删除指定用户的一条通知记录"""
        result = await db.execute(
            delete(NotificationUser).where(
                NotificationUser.notification_id == notification_id,
                NotificationUser.recipient_id == user_id,
            )
        )
        deleted = result.rowcount
        if deleted:
            # 如果没有其他用户引用此通知，一并删除 Notification 本体
            remaining = await db.execute(
                select(NotificationUser).where(NotificationUser.notification_id == notification_id)
            )
            if not remaining.scalars().first():
                await db.execute(delete(Notification).where(Notification.id == notification_id))
                logger.debug("Deleted orphan notification #%s", notification_id)
        return deleted > 0

    async def cleanup_read(self, db: AsyncSession, days: int = 7) -> int:
        """清理已读通知：days=0 清除全部已读，days>0 清除 N 天前的已读通知"""
        if days > 0:
            threshold = datetime.now() - timedelta(days=days)
            result = await db.execute(
                select(Notification.id).where(Notification.created_at < threshold)
            )
            old_ids = [row[0] for row in result.all()]
            if not old_ids:
                return 0
        else:
            # days=0: 清除全部已读
            all_result = await db.execute(select(Notification.id))
            old_ids = [row[0] for row in all_result.all()]
            if not old_ids:
                return 0

        # 删除已读的 notification_user 记录
        nu_result = await db.execute(
            delete(NotificationUser).where(
                NotificationUser.notification_id.in_(old_ids),
                NotificationUser.is_read == True,
            )
        )
        deleted = nu_result.rowcount

        # 清理孤立的 Notification
        orphan_result = await db.execute(
            delete(Notification).where(
                Notification.id.in_(old_ids),
                ~Notification.id.in_(
                    select(NotificationUser.notification_id).where(NotificationUser.notification_id.in_(old_ids))
                )
            )
        )
        orph = orphan_result.rowcount
        logger.info("Cleanup: deleted %s read notification_user records, %s orphan notifications", deleted, orph)
        return deleted + orph


notification_service = NotificationService()
