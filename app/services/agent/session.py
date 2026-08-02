"""多会话记忆：每个窗口独立历史 + 事实表，带 LRU/TTL 与上下文预算裁剪。"""
import time
import uuid
from typing import Any


class SessionStore:
    def __init__(self, ttl: int = 1800, max_sessions: int = 20, max_messages: int = 20):
        self.ttl = ttl
        self.max_sessions = max_sessions
        self.max_messages = max_messages
        self._sessions: dict[str, dict[str, Any]] = {}

    def _now(self) -> float:
        return time.time()

    def create(self, user_id: str) -> dict[str, Any]:
        now = self._now()
        session = {
            "session_id": uuid.uuid4().hex,
            "user_id": user_id,
            "created_at": now,
            "updated_at": now,
            "messages": [],
            "facts": [],
        }
        self._sessions[session["session_id"]] = session
        self._evict(user_id)
        return session

    def get(self, user_id: str, session_id: str) -> dict[str, Any] | None:
        session = self._sessions.get(session_id)
        if not session or session["user_id"] != user_id:
            return None
        if self._now() - session["updated_at"] > self.ttl:
            self._sessions.pop(session_id, None)
            return None
        session["updated_at"] = self._now()
        return session

    def list_sessions(self, user_id: str) -> list[dict[str, Any]]:
        return [
            {
                "session_id": s["session_id"],
                "created_at": s["created_at"],
                "updated_at": s["updated_at"],
                "message_count": len(s["messages"]),
            }
            for s in self._sessions.values()
            if s["user_id"] == user_id
        ]

    def delete(self, user_id: str, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session or session["user_id"] != user_id:
            return False
        self._sessions.pop(session_id, None)
        return True

    def add_message(self, user_id: str, session_id: str, role: str, content: str, kind: str = "text") -> None:
        session = self.get(user_id, session_id)
        if not session:
            return
        session["messages"].append({"role": role, "content": content, "kind": kind, "ts": self._now()})
        if len(session["messages"]) > self.max_messages:
            session["messages"] = session["messages"][-self.max_messages:]

    def add_fact(self, user_id: str, session_id: str, fact: str) -> None:
        session = self.get(user_id, session_id)
        if not session:
            return
        if fact not in session["facts"]:
            session["facts"].append(fact)

    def build_context(self, user_id: str, session_id: str, budget_tokens: int = 8000) -> list[dict[str, str]]:
        """按优先级组装：事实表优先，历史从最新往前装，超预算丢弃最旧。"""
        session = self.get(user_id, session_id)
        if not session:
            return []
        parts: list[dict[str, str]] = []
        if session["facts"]:
            parts.append({"role": "system", "content": "对话内已发生的动作事实：" + "；".join(session["facts"])})
        used = sum(self.estimate_tokens(p["content"]) for p in parts)
        for msg in reversed(session["messages"]):
            cost = self.estimate_tokens(msg["content"])
            if used + cost > budget_tokens:
                break
            parts.append({"role": msg["role"], "content": msg["content"]})
            used += cost
        return parts

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """简易估算：中文字符×0.7 + 其他单词数。"""
        cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
        other = len(text.split())
        return max(1, int(cjk * 0.7 + other))

    def _evict(self, user_id: str) -> None:
        user_sessions = [s for s in self._sessions.values() if s["user_id"] == user_id]
        if len(user_sessions) <= self.max_sessions:
            return
        user_sessions.sort(key=lambda s: s["updated_at"])
        for old in user_sessions[: len(user_sessions) - self.max_sessions]:
            self._sessions.pop(old["session_id"], None)
