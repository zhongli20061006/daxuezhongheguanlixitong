"""确认令牌：创建、消费（一次性）、过期、跨用户隔离"""
import time

from app.services.agent.confirmations import ConfirmationStore


def test_create_and_consume_once():
    store = ConfirmationStore(ttl=300)
    token = store.create("S2024001", {"action": "enroll", "schedule_id": 5})
    payload = store.consume("S2024001", token)
    assert payload == {"action": "enroll", "schedule_id": 5}
    # 一次性：再次消费返回 None
    assert store.consume("S2024001", token) is None


def test_wrong_user_cannot_consume():
    store = ConfirmationStore(ttl=300)
    token = store.create("S2024001", {"action": "enroll"})
    assert store.consume("S2024002", token) is None
    assert store.consume("S2024001", token) is not None


def test_expired_token(monkeypatch):
    store = ConfirmationStore(ttl=300)
    token = store.create("S2024001", {"action": "enroll"})
    monkeypatch.setattr(store, "_now", lambda: time.time() + 301)
    assert store.consume("S2024001", token) is None


def test_unknown_token():
    store = ConfirmationStore(ttl=300)
    assert store.consume("S2024001", "nope") is None
