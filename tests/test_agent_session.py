"""会话记忆：多窗口隔离、LRU 上限、TTL、上下文预算裁剪、事实表。"""
import time

from app.services.agent.session import SessionStore


def test_create_get_ownership():
    store = SessionStore()
    sess = store.create("S2024001")
    assert store.get("S2024001", sess["session_id"]) is not None
    assert store.get("S2024002", sess["session_id"]) is None


def test_list_and_delete():
    store = SessionStore()
    a = store.create("u1")
    b = store.create("u1")
    assert len(store.list_sessions("u1")) == 2
    assert store.delete("u1", a["session_id"]) is True
    assert store.delete("u2", b["session_id"]) is False
    assert len(store.list_sessions("u1")) == 1


def test_lru_eviction():
    store = SessionStore(max_sessions=2)
    a = store.create("u1")
    store.create("u1")
    c = store.create("u1")
    assert store.get("u1", a["session_id"]) is None
    assert store.get("u1", c["session_id"]) is not None


def test_ttl_expiry(monkeypatch):
    store = SessionStore(ttl=30)
    sess = store.create("u1")
    monkeypatch.setattr(store, "_now", lambda: time.time() + 31)
    assert store.get("u1", sess["session_id"]) is None


def test_context_budget_trims_oldest():
    store = SessionStore(max_messages=10)
    sess = store.create("u1")
    store.add_message("u1", sess["session_id"], "user", "预" * 43)
    store.add_message("u1", sess["session_id"], "assistant", "复" * 43)
    ctx = store.build_context("u1", sess["session_id"], budget_tokens=50)
    assert ctx == [{"role": "assistant", "content": "复" * 43}]  # 预算只装得下最新一条


def test_facts_included_in_context():
    store = SessionStore()
    sess = store.create("u1")
    store.add_fact("u1", sess["session_id"], "已选课：高等数学")
    ctx = store.build_context("u1", sess["session_id"], budget_tokens=8000)
    assert "高等数学" in ctx[0]["content"]


def test_pending_write_roundtrip():
    store = SessionStore()
    sess = store.create("u1")
    store.set_pending_write("u1", sess["session_id"], "leave_apply", {"start_date": "2026-08-05"})
    pending = store.get_pending_write("u1", sess["session_id"])
    assert pending["intent"] == "leave_apply"
    assert pending["params"]["start_date"] == "2026-08-05"
    store.clear_pending_write("u1", sess["session_id"])
    assert store.get_pending_write("u1", sess["session_id"]) is None


def test_pending_write_expires(monkeypatch):
    store = SessionStore()
    sess = store.create("u1")
    store.set_pending_write("u1", sess["session_id"], "leave_apply", {})
    monkeypatch.setattr(store, "_now", lambda: time.time() + 301)
    assert store.get_pending_write("u1", sess["session_id"]) is None
