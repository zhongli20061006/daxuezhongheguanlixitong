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

    async def mark_as_read(self, db: AsyncSession, notification_id: int, user_id: str, role: str) -> bool:
        """标记该通知中当前用户可见范围内（定向本人/本角色/全局）的行为已读。

        返回是否命中了可见记录；未命中说明该通知不属于当前用户可见范围。
        """
        result = await db.execute(
            update(NotificationUser)
            .where(
                NotificationUser.notification_id == notification_id,
                or_(
                    NotificationUser.recipient_id == user_id,
                    NotificationUser.recipient_role == role,
                    and_(NotificationUser.recipient_id.is_(None), NotificationUser.recipient_role.is_(None)),
                )
            )
            .values(is_read=True)
        )
        return result.rowcount > 0

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

    async def cleanup_read(
        self, db: AsyncSession, days: int = 7, user_id: str | None = None, is_admin: bool = False
    ) -> int:
        """清理已读通知。

        - is_admin=True：保留全局语义（清理所有用户的已读记录及孤儿通知）
        - 普通用户：仅清理自己名下（recipient_id == user_id）的已读定向通知，
          不触碰其他用户的记录以及共享的角色级/全局行。
        """
        if is_admin:
            return await self._cleanup_read_global(db, days)

        # 普通用户：自己的已读定向通知 id
        own_ids = select(NotificationUser.notification_id).where(
            NotificationUser.recipient_id == user_id,
            NotificationUser.is_read == True,
        )
        if days > 0:
            threshold = datetime.now() - timedelta(days=days)
            result = await db.execute(
                select(Notification.id).where(
                    Notification.id.in_(own_ids),
                    Notification.created_at < threshold,
                )
            )
        else:
            result = await db.execute(own_ids)
        old_ids = [row[0] for row in result.all()]
        if not old_ids:
            return 0

        # 删除该用户自己的已读记录
        nu_result = await db.execute(
            delete(NotificationUser).where(
                NotificationUser.notification_id.in_(old_ids),
                NotificationUser.recipient_id == user_id,
                NotificationUser.is_read == True,
            )
        )
        deleted = nu_result.rowcount

        # 清理孤立的 Notification（不再被任何 NotificationUser 引用）
        orphan_result = await db.execute(
            delete(Notification).where(
                Notification.id.in_(old_ids),
                ~Notification.id.in_(
                    select(NotificationUser.notification_id).where(NotificationUser.notification_id.in_(old_ids))
                )
            )
        )
        orph = orphan_result.rowcount
        logger.info("Cleanup(user=%s): deleted %s read notification_user records, %s orphan notifications", user_id, deleted, orph)
        return deleted + orph

    async def _cleanup_read_global(self, db: AsyncSession, days: int = 7) -> int:
        """全局清理已读通知（仅管理员使用）。"""
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
        logger.info("Cleanup(global): deleted %s read notification_user records, %s orphan notifications", deleted, orph)
        return deleted + orph


notification_service = NotificationService()
