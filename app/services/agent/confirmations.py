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

    def consume_latest(self, user_id: str) -> dict[str, Any] | None:
        """取出该用户最近一次未过期的待确认操作（用于对话内文本确认）。"""
        now = self._now()
        best_token: str | None = None
        best_expires = -1.0
        for token, item in self._items.items():
            if item["user_id"] != user_id or now > item["expires_at"]:
                continue
            if item["expires_at"] > best_expires:
                best_expires = item["expires_at"]
                best_token = token
        if best_token is None:
            return None
        payload = self._items[best_token]["payload"]
        self._items.pop(best_token, None)
        return payload

    def discard_latest(self, user_id: str) -> bool:
        """丢弃该用户最近一次待确认操作，返回是否确有操作被丢弃。"""
        now = self._now()
        best_token: str | None = None
        best_expires = -1.0
        for token, item in self._items.items():
            if item["user_id"] != user_id or now > item["expires_at"]:
                continue
            if item["expires_at"] > best_expires:
                best_expires = item["expires_at"]
                best_token = token
        if best_token is None:
            return False
        self._items.pop(best_token, None)
        return True
