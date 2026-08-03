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


def test_consume_latest_returns_newest_and_is_one_shot():
    store = ConfirmationStore(ttl=300)
    store.create("S2024001", {"action": "enroll", "seq": 1})
    store.create("S2024001", {"action": "leave_apply", "seq": 2})
    store.create("S2024002", {"action": "enroll", "seq": 99})  # 其他用户不受影响
    assert store.consume_latest("S2024001") == {"action": "leave_apply", "seq": 2}
    assert store.consume_latest("S2024001") == {"action": "enroll", "seq": 1}
    assert store.consume_latest("S2024001") is None
    assert store.consume_latest("S2024002") == {"action": "enroll", "seq": 99}


def test_consume_latest_skips_expired(monkeypatch):
    store = ConfirmationStore(ttl=300)
    store.create("S2024001", {"action": "enroll"})
    monkeypatch.setattr(store, "_now", lambda: time.time() + 301)
    assert store.consume_latest("S2024001") is None


def test_discard_latest():
    store = ConfirmationStore(ttl=300)
    store.create("S2024001", {"action": "enroll"})
    assert store.discard_latest("S2024001") is True
    assert store.discard_latest("S2024001") is False
