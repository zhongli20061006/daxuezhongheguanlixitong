"""
事件总线
提供发布/订阅模式用于解耦业务逻辑与通知逻辑
"""
import asyncio
import logging
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class Events:
    ENROLL_SUCCESS = "enroll_success"
    DROP_COURSE = "drop_course"
    SCORE_UPDATED = "score_updated"
    SCORE_PUBLISHED = "score_published"
    LEAVE_SUBMITTED = "leave_submitted"
    LEAVE_APPROVED = "leave_approved"
    LEAVE_REJECTED = "leave_rejected"
    REPAIR_STATUS_CHANGED = "repair_status_changed"
    PASSWORD_RESET = "password_reset"
    SELECTION_WINDOW_OPEN = "selection_window_open"


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable[..., Awaitable[None]]]] = {}
        self._tasks: set[asyncio.Task] = set()

    def subscribe(self, event: str, handler: Callable[..., Awaitable[None]]):
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def unsubscribe(self, event: str, handler: Callable[..., Awaitable[None]]):
        if event in self._handlers:
            self._handlers[event].remove(handler)

    async def emit(self, event: str, **kwargs: Any):
        handlers = self._handlers.get(event, [])
        for handler in handlers:
            task = asyncio.create_task(self._safe_run(handler, **kwargs))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def _safe_run(self, handler: Callable[..., Awaitable[None]], **kwargs: Any):
        try:
            await handler(**kwargs)
        except Exception as e:
            logger.error(f"Event handler {handler.__name__} failed: {e}", exc_info=True)

    async def emit_sync(self, event: str, **kwargs: Any):
        """同步等待所有 handler 执行完毕"""
        handlers = self._handlers.get(event, [])
        for handler in handlers:
            await self._safe_run(handler, **kwargs)


event_bus = EventBus()
