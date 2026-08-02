"""一次性确认令牌：写操作执行前必须经用户确认。"""
import time
import uuid
from typing import Any


class ConfirmationStore:
    def __init__(self, ttl: int = 300):
        self._ttl = ttl
        self._items: dict[str, dict[str, Any]] = {}

    def _now(self) -> float:
        return time.time()

    def create(self, user_id: str, payload: dict[str, Any]) -> str:
        token = uuid.uuid4().hex
        self._items[token] = {
            "user_id": user_id,
            "payload": payload,
            "expires_at": self._now() + self._ttl,
        }
        return token

    def consume(self, user_id: str, token: str) -> dict[str, Any] | None:
        item = self._items.get(token)
        if not item:
            return None
        if item["user_id"] != user_id:
            return None
        if self._now() > item["expires_at"]:
            self._items.pop(token, None)
            return None
        self._items.pop(token, None)
        return item["payload"]
