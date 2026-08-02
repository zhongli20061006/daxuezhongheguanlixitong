"""种子数据保证：agent01 一周每天有课；可选课程余量>0、窗口开放、无冲突（预检必过）。"""
import pytest
from sqlalchemy import select

from app.models import (
    Classroom, CourseCapacity, Schedule, Student, StudentClass, Subject, SubjectType,
    SystemConfig, Teacher,
)
from app.services.agent.actions import ActionExecutor
from app.services.agent.confirmations import ConfirmationStore
from app.services.agent.session import SessionStore


class FakeLLM:
    async def chat(self, messages):
        return "x"

    async def extract_json(self, messages):
        raise Exception("down")


async def _cleanup(test_engine):
    from sqlalchemy import delete as sa_delete

    from app.models import (
        Classroom, CourseCapacity, CourseSelection, Schedule, Student, StudentClass,
        Subject, SystemConfig, Teacher,
    )
    async with test_engine.begin() as conn:
        for model in (CourseSelection, CourseCapacity, Schedule, SystemConfig, Student, Classroom, Subject, Teacher, StudentClass):
            await conn.execute(sa_delete(model))


async def _build_seed(db, test_engine):
    """构造等价于 init_data.py 中 agent01 的种子：班级1 + 周一~周日各一节课 + 可选课程。"""
    await _cleanup(test_engine)
    db.add_all([
        StudentClass(id=1, name="2024计算机1班", major="计算机科学与技术", grade=2024, advisor_id=1),
        Teacher(id=1, name="张老师", job_number="T10001", department="计算机", title="教授", is_college_admin=False),
        Subject(id=1, name="高等数学", credit=5.0, type=SubjectType.compulsory),
        Subject(id=2, name="大学英语", credit=4.0, type=SubjectType.compulsory),
        Subject(id=11, name="人工智能实战", credit=2.0, type=SubjectType.elective),
        Classroom(id=1, name="D101", capacity=60, building="D", has_projector=False),
        Classroom(id=9, name="D401", capacity=120, building="D", has_projector=True),
        Student(id="agent01", name="智能体测试员", class_id=1),
        SystemConfig(config_key="selection_start_time", config_value="2020-01-01 08:00:00"),
        SystemConfig(config_key="selection_end_time", config_value="2099-12-31 18:00:00"),
    ])
    await db.flush()
    for dow in range(1, 8):
        db.add(Schedule(
            teacher_id=1, subject_id=1 if dow % 2 else 2, class_id=1, classroom_id=1,
            weeks="1-18", day_of_week=dow, period=f"{dow}-{dow}", semester="2024-2025-1",
        ))
        await db.flush()
    elective = Schedule(
        teacher_id=1, subject_id=11, class_id=1, classroom_id=9,
        weeks="1-18", day_of_week=7, period="9-10", semester="2024-2025-1",
    )
    db.add(elective)
    await db.flush()
    elective_id = elective.id
    db.add(CourseCapacity(schedule_id=elective.id, enrolled=0, capacity=30))
    await db.commit()
    return elective_id


@pytest.mark.asyncio
async def test_agent01_has_class_every_day(db, test_engine):
    await _build_seed(db, test_engine)
    days = set((await db.execute(select(Schedule.day_of_week).where(Schedule.class_id == 1))).scalars().all())
    assert days >= set(range(1, 8))


@pytest.mark.asyncio
async def test_agent01_enroll_precheck_passes(db, test_engine):
    elective_id = await _build_seed(db, test_engine)
    executor = ActionExecutor(FakeLLM(), ConfirmationStore(), SessionStore())
    ok, reason, info = await executor._precheck_enroll("agent01", elective_id, db)
    assert ok, reason
    assert info["capacity"] >= 1
