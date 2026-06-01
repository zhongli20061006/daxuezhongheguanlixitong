"""
WebSocket 连接管理器
管理 userId -> WebSocket 连接的映射，支持单播和广播
"""
from fastapi import WebSocket
from collections import defaultdict


class WebSocketManager:
    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        self._connections[user_id].add(ws)

    async def disconnect(self, user_id: str, ws: WebSocket):
        self._connections[user_id].discard(ws)
        if not self._connections[user_id]:
            del self._connections[user_id]
        try:
            await ws.close()
        except Exception:
            pass

    async def send(self, user_id: str, data: dict):
        dead: list[WebSocket] = []
        for ws in self._connections.get(user_id, set()):
            try:
                from fastapi.encoders import jsonable_encoder
                await ws.send_json(jsonable_encoder(data))
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(user_id, ws)

    async def broadcast(self, data: dict, role: str | None = None):
        from fastapi.encoders import jsonable_encoder
        dead: list[tuple[str, WebSocket]] = []
        for uid, sockets in self._connections.items():
            for ws in sockets:
                try:
                    await ws.send_json(jsonable_encoder(data))
                except Exception:
                    dead.append((uid, ws))
        for uid, ws in dead:
            await self.disconnect(uid, ws)

    @property
    def online_count(self) -> int:
        return sum(len(v) for v in self._connections.values())


ws_manager = WebSocketManager()
