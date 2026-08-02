"""动作执行器：权限、课表查询、学习方案降级、选课预检与确认执行。"""
from sqlalchemy import select

import pytest

from app.models import (
    Classroom, CourseCapacity, CourseSelection, Schedule, Student, StudentClass,
    Subject, SubjectType, SystemConfig, Teacher,
)
from app.services.agent.actions import ActionExecutor, _tomorrow_weekday
from app.services.agent.confirmations import ConfirmationStore
from app.services.agent.intent import Intent, IntentType
from app.services.agent.llm import OllamaUnavailable
from app.services.agent.session import SessionStore


class FakeLLM:
    def __init__(self):
        self.replies = []

    async def chat(self, messages):
        return "模型回复"

    async def extract_json(self, messages):
        raise OllamaUnavailable("down")  # 强制学习方案走模板降级


async def _cleanup(test_engine):
    """清空 agent 相关表，避免共享 sqlite 的跨用例残留。"""
    from sqlalchemy import delete as sa_delete

    from app.models import (
        Classroom, CourseCapacity, CourseSelection, Schedule, Student, StudentClass,
        Subject, SystemConfig, Teacher,
    )
    async with test_engine.begin() as conn:
        for model in (CourseSelection, CourseCapacity, Schedule, SystemConfig, Student, Classroom, Subject, Teacher, StudentClass):
            await conn.execute(sa_delete(model))


async def _seed(db, test_engine):
    await _cleanup(test_engine)
    db.add_all([
        StudentClass(id=1, name="测试班", major="计算机科学与技术", grade=2024, advisor_id=1),
        Teacher(id=1, name="张老师", job_number="T10001", department="计算机", title="教授", is_college_admin=False),
        Subject(id=1, name="高等数学", credit=5.0, type=SubjectType.compulsory),
        Subject(id=2, name="人工智能实战", credit=2.0, type=SubjectType.elective),
        Classroom(id=1, name="D101", capacity=60, building="教学楼D", has_projector=False),
        Student(id="S2024001", name="测试学生", class_id=1),
        SystemConfig(config_key="selection_start_time", config_value="2020-01-01 08:00:00"),
        SystemConfig(config_key="selection_end_time", config_value="2099-12-31 18:00:00"),
    ])
    await db.flush()
    db.add(Schedule(
        id=1, teacher_id=1, subject_id=2, class_id=1, classroom_id=1,
        weeks="1-18", day_of_week=_tomorrow_weekday(), period="5-6", semester="2024-2025-1",
    ))
    db.add(CourseCapacity(schedule_id=1, enrolled=0, capacity=30))
    await db.commit()


def _executor():
    return ActionExecutor(FakeLLM(), ConfirmationStore(), SessionStore())


@pytest.mark.asyncio
async def test_permission_student_only(db):
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.query_schedule), "T10001", "teacher", "s", db
    )
    assert msgs[0].kind == "error"


@pytest.mark.asyncio
async def test_navigate_validates_page(db):
    executor = _executor()
    ok = await executor.execute(
        Intent(intent=IntentType.navigate, params={"page": "/selection"}), "u1", "student", "s", db
    )
    assert ok[0].kind == "card"
    bad = await executor.execute(
        Intent(intent=IntentType.navigate, params={"page": "/evil"}), "u1", "student", "s", db
    )
    assert bad[0].kind == "error"


@pytest.mark.asyncio
async def test_enroll_confirmation_then_execute(db, test_engine):
    await _seed(db, test_engine)
    executor = _executor()
    intent = Intent(intent=IntentType.enroll, params={"course": "人工智能实战"}, need_confirm=True)
    msgs = await executor.execute(intent, "S2024001", "student", "sess1", db)
    assert msgs[0].kind == "confirmation"
    token = msgs[0].confirm_token
    results = await executor.execute_confirm(
        executor.confirmations.consume("S2024001", token), db
    )
    assert results[0].kind == "card"
    cap = (await db.execute(
        select(CourseCapacity).where(CourseCapacity.schedule_id == 1)
    )).scalar_one()
    assert cap.enrolled == 1


@pytest.mark.asyncio
async def test_enroll_full_fails(db, test_engine):
    await _seed(db, test_engine)
    executor = _executor()
    cap = (await db.execute(
        select(CourseCapacity).where(CourseCapacity.schedule_id == 1)
    )).scalar_one()
    cap.enrolled = cap.capacity
    await db.commit()
    msgs = await executor.execute(
        Intent(intent=IntentType.enroll, params={"course": "人工智能实战"}, need_confirm=True),
        "S2024001", "student", "sess1", db,
    )
    assert msgs[0].kind == "error"
    assert "已满" in msgs[0].content


@pytest.mark.asyncio
async def test_conflict_detected(db, test_engine):
    await _seed(db, test_engine)
    db.add(Schedule(
        id=99, teacher_id=1, subject_id=1, class_id=1, classroom_id=1,
        weeks="1-18", day_of_week=_tomorrow_weekday(), period="5-6", semester="2024-2025-1",
    ))
    await db.commit()
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.enroll, params={"course": "人工智能实战"}, need_confirm=True),
        "S2024001", "student", "sess1", db,
    )
    assert msgs[0].kind == "error"
    assert "冲突" in msgs[0].content


@pytest.mark.asyncio
async def test_study_plan_template_fallback(db, test_engine):
    await _seed(db, test_engine)
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.study_plan), "S2024001", "student", "sess1", db
    )
    assert msgs[0].kind == "card"
    assert "人工智能实战" in msgs[0].content


@pytest.mark.asyncio
async def test_query_schedule_tomorrow(db, test_engine):
    await _seed(db, test_engine)
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.query_schedule), "S2024001", "student", "sess1", db
    )
    assert msgs[0].kind == "card"
    assert msgs[0].data["courses"][0]["course"] == "人工智能实战"
