"""智能体 API：chat、confirm、status、sessions。"""
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models import (
    ApprovalConfig, ApprovalRecord, Classroom, ClassroomReservation, CourseCapacity,
    CourseSelection, LeaveApplication, Notification, NotificationUser, Repair, Schedule,
    Student, StudentClass, Subject, SubjectType, SystemConfig, Teacher,
)
from app.services.agent.actions import _tomorrow_weekday
from app.services.agent.llm import OllamaUnavailable


class FakeLLM:
    async def extract_json(self, messages):
        raise OllamaUnavailable("down")

    async def chat(self, messages):
        return "模型回复"

    async def ping(self):
        return True

    def status(self):
        return "ok"


class FakeMultiLLM(FakeLLM):
    async def extract_json(self, messages):
        return {"intents": [
            {"intent": "enroll", "params": {"course": "不存在的课"}, "confidence": 0.9},
            {"intent": "query_schedule", "params": {}, "confidence": 0.9},
        ]}


async def _cleanup(test_engine):
    from sqlalchemy import delete as sa_delete

    async with test_engine.begin() as conn:
        for model in (
            NotificationUser, Notification, ApprovalRecord, LeaveApplication,
            ClassroomReservation, Repair, ApprovalConfig,
            CourseSelection, CourseCapacity, Schedule, SystemConfig,
            Student, Classroom, Subject, Teacher, StudentClass,
        ):
            await conn.execute(sa_delete(model))


async def _seed_agent_data(db, test_engine):
    await _cleanup(test_engine)
    db.add_all([
        StudentClass(id=1, name="测试班", major="计算机", grade=2024, advisor_id=1),
        Teacher(id=1, name="张老师", job_number="T10001", department="计算机", title="教授", is_college_admin=False),
        Subject(id=1, name="高等数学", credit=5.0, type=SubjectType.compulsory),
        Subject(id=2, name="人工智能实战", credit=2.0, type=SubjectType.elective),
        Classroom(id=1, name="D101", capacity=60, building="D", has_projector=False),
        Student(id="S2024001", name="测试学生", class_id=1),
        SystemConfig(config_key="selection_start_time", config_value="2020-01-01 08:00:00"),
        SystemConfig(config_key="selection_end_time", config_value="2099-12-31 18:00:00"),
    ])
    await db.flush()
    db.add(Schedule(
        id=1, teacher_id=1, subject_id=2, class_id=1, classroom_id=1,
        weeks="1-18", day_of_week=5, period="5-6", semester="2024-2025-1",
    ))
    db.add(CourseCapacity(schedule_id=1, enrolled=0, capacity=30))
    db.add(Schedule(
        id=2, teacher_id=1, subject_id=1, class_id=1, classroom_id=1,
        weeks="1-18", day_of_week=_tomorrow_weekday(), period="1-2", semester="2024-2025-1",
    ))
    await db.commit()


@pytest.fixture
def auth_override():
    from app.deps import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: {
        "username": "S2024001", "role": "student", "role_id": "S2024001",
    }
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def fake_llm(monkeypatch):
    from app.api import agent as agent_api

    fake = FakeLLM()
    monkeypatch.setattr(agent_api, "agent_llm", fake)
    monkeypatch.setattr(agent_api.resolver, "llm", fake)
    monkeypatch.setattr(agent_api.executor, "llm", fake)
    return fake


@pytest.mark.asyncio
async def test_chat_enroll_confirmation(client, db, test_engine, auth_override, fake_llm):
    await _seed_agent_data(db, test_engine)
    resp = await client.post("/agent/chat", json={"message": "帮我选人工智能实战"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"]
    kinds = [m["kind"] for m in data["messages"]]
    assert "confirmation" in kinds
    assert "summary" in kinds


@pytest.mark.asyncio
async def test_confirm_executes_enroll(client, db, test_engine, auth_override, fake_llm):
    await _seed_agent_data(db, test_engine)
    resp = await client.post("/agent/chat", json={"message": "帮我选人工智能实战"})
    token = next(m["confirm_token"] for m in resp.json()["messages"] if m["kind"] == "confirmation")
    resp2 = await client.post("/agent/confirm", json={"token": token})
    assert resp2.status_code == 200
    assert resp2.json()["messages"][0]["kind"] == "card"


@pytest.mark.asyncio
async def test_confirm_expired_token(client, auth_override, fake_llm):
    resp = await client.post("/agent/confirm", json={"token": "not-a-token"})
    assert resp.status_code == 200
    assert resp.json()["messages"][0]["kind"] == "error"


@pytest.mark.asyncio
async def test_multi_intent_business_failure_continues(client, db, test_engine, auth_override, monkeypatch):
    """第一个意图业务失败（课程不存在）后，同一消息中的只读意图仍继续执行。"""
    await _seed_agent_data(db, test_engine)
    from app.api import agent as agent_api

    fake = FakeMultiLLM()
    monkeypatch.setattr(agent_api, "agent_llm", fake)
    monkeypatch.setattr(agent_api.resolver, "llm", fake)
    monkeypatch.setattr(agent_api.executor, "llm", fake)
    resp = await client.post("/agent/chat", json={"message": "帮我选不存在的课，然后查明天的课表"})
    assert resp.status_code == 200
    kinds = [m["kind"] for m in resp.json()["messages"]]
    assert kinds.count("error") >= 1
    assert "card" in kinds
    assert "summary" in kinds


@pytest.mark.asyncio
async def test_status_and_sessions(client, auth_override, fake_llm):
    status = await client.get("/agent/status")
    assert status.status_code == 200
    assert status.json()["ollama"] == "ok"
    resp = await client.get("/agent/sessions")
    assert resp.status_code == 200
    assert "sessions" in resp.json()


@pytest.mark.asyncio
async def test_session_history_endpoint(client, db, test_engine, auth_override, fake_llm):
    await _seed_agent_data(db, test_engine)
    resp = await client.post("/agent/chat", json={"message": "帮我选人工智能实战"})
    sid = resp.json()["session_id"]
    resp2 = await client.get(f"/agent/sessions/{sid}")
    assert resp2.status_code == 200
    msgs = resp2.json()["messages"]
    assert any(m["role"] == "user" for m in msgs)
    assert any(m["kind"] == "confirmation" for m in msgs)

    missing = await client.get("/agent/sessions/not-exist")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_role_id_identity_when_username_differs(client, db, test_engine, monkeypatch):
    """agent01 这类测试账号 username 与 student.id 不一致时，业务身份必须用 role_id。"""
    await _seed_agent_data(db, test_engine)
    db.add(Student(id="S2024099", name="智能体测试员", class_id=1))
    await db.commit()

    from app.deps import get_current_user
    from app.main import app
    from app.api import agent as agent_api

    app.dependency_overrides[get_current_user] = lambda: {
        "username": "agent01", "role": "student", "role_id": "S2024099",
    }
    fake = FakeLLM()
    monkeypatch.setattr(agent_api, "agent_llm", fake)
    monkeypatch.setattr(agent_api.resolver, "llm", fake)
    monkeypatch.setattr(agent_api.executor, "llm", fake)
    try:
        resp = await client.post("/agent/chat", json={"message": "明天上什么课"})
        assert resp.status_code == 200
        data = resp.json()
        card = next(m for m in data["messages"] if m["kind"] == "card")
        assert card["title"] == "明天的课表"
        assert len(card["data"]["courses"]) == 1  # 高等数学（明天）

        resp2 = await client.post("/agent/chat", json={"message": "帮我选人工智能实战"})
        kinds = [m["kind"] for m in resp2.json()["messages"]]
        assert "confirmation" in kinds
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_chat_leave_confirmation_and_confirm(client, db, test_engine, auth_override, fake_llm):
    """规则兜底下：请假意图参数抽取 → 确认卡片 → 确认后真实创建请假单。"""
    await _seed_agent_data(db, test_engine)
    start = date.today() + timedelta(days=2)
    msg = f"我要请假 {start.isoformat()} 到 {(start + timedelta(days=1)).isoformat()} 因为感冒"
    resp = await client.post("/agent/chat", json={"message": msg})
    assert resp.status_code == 200
    data = resp.json()
    kinds = [m["kind"] for m in data["messages"]]
    assert "confirmation" in kinds
    token = next(m["confirm_token"] for m in data["messages"] if m["kind"] == "confirmation")
    resp2 = await client.post("/agent/confirm", json={"token": token})
    assert resp2.status_code == 200
    assert resp2.json()["messages"][0]["kind"] == "card"
    leaves = (await db.execute(select(LeaveApplication))).scalars().all()
    assert len(leaves) == 1
    assert leaves[0].student_id == "S2024001"


@pytest.mark.asyncio
async def test_chat_repair_confirmation_and_confirm(client, db, test_engine, auth_override, fake_llm):
    """规则兜底下：报修意图参数抽取 → 确认卡片 → 确认后真实创建报修单。"""
    await _seed_agent_data(db, test_engine)
    resp = await client.post("/agent/chat", json={
        "message": "我要报修，地点D101，投影仪坏了，类型电子产品",
    })
    assert resp.status_code == 200
    data = resp.json()
    kinds = [m["kind"] for m in data["messages"]]
    assert "confirmation" in kinds
    token = next(m["confirm_token"] for m in data["messages"] if m["kind"] == "confirmation")
    resp2 = await client.post("/agent/confirm", json={"token": token})
    assert resp2.status_code == 200
    assert resp2.json()["messages"][0]["kind"] == "card"
    repairs = (await db.execute(select(Repair))).scalars().all()
    assert len(repairs) == 1
    assert repairs[0].location == "D101"
    assert repairs[0].type == "电子产品"


@pytest.mark.asyncio
async def test_chat_reserve_confirmation_and_confirm(client, db, test_engine, auth_override, fake_llm):
    """规则兜底下：预约教室意图参数抽取 → 确认卡片 → 确认后真实创建预约。"""
    await _seed_agent_data(db, test_engine)
    resp = await client.post("/agent/chat", json={
        "message": "帮我预约教室D101，第1周周一3-4节，用于班会",
    })
    assert resp.status_code == 200
    data = resp.json()
    kinds = [m["kind"] for m in data["messages"]]
    assert "confirmation" in kinds
    token = next(m["confirm_token"] for m in data["messages"] if m["kind"] == "confirmation")
    resp2 = await client.post("/agent/confirm", json={"token": token})
    assert resp2.status_code == 200
    assert resp2.json()["messages"][0]["kind"] == "card"
    reservations = (await db.execute(select(ClassroomReservation))).scalars().all()
    assert len(reservations) == 1
    assert reservations[0].classroom_id == 1
    assert reservations[0].week == 1
