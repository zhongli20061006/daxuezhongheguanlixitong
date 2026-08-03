"""成绩写入服务：插入/更新、总评自动计算，以及 API 手动录入回归。"""
import pytest
from sqlalchemy import select

from app.models import (
    Classroom, CourseCapacity, CourseSelection, Schedule, Score, ScoreType,
    Student, StudentClass, Subject, SubjectType, Teacher,
)
from app.services.score_service import auto_calculate_total_if_ready, record_score


async def _seed_score(db, test_engine):
    from tests.test_agent_actions import _cleanup

    await _cleanup(test_engine)
    db.add_all([
        StudentClass(id=1, name="测试班", major="计算机", grade=2024, advisor_id=1),
        Teacher(id=1, name="张老师", job_number="T10001", department="计算机", title="教授", is_college_admin=False),
        Subject(id=1, name="高等数学", credit=5.0, type=SubjectType.compulsory),
        Classroom(id=1, name="D101", capacity=60, building="D", has_projector=False),
        Student(id="S2024001", name="测试学生", class_id=1),
    ])
    await db.flush()
    db.add(Schedule(
        id=1, teacher_id=1, subject_id=1, class_id=1, classroom_id=1,
        weeks="1-18", day_of_week=1, period="1-2", semester="2024-2025-1",
    ))
    db.add(CourseCapacity(schedule_id=1, enrolled=1, capacity=30))
    db.add(CourseSelection(student_id="S2024001", schedule_id=1, status=1))
    await db.commit()


@pytest.mark.asyncio
async def test_record_score_insert_then_update(db, test_engine):
    await _seed_score(db, test_engine)
    inserted, updated = await record_score(
        db, schedule_id=1, student_id="S2024001", score=88, score_type="期末",
    )
    assert (inserted, updated) == (1, 0)
    inserted2, updated2 = await record_score(
        db, schedule_id=1, student_id="S2024001", score=95, score_type="期末",
    )
    assert (inserted2, updated2) == (0, 1)
    rows = (await db.execute(select(Score))).scalars().all()
    assert len(rows) == 1
    assert rows[0].score == 95


@pytest.mark.asyncio
async def test_auto_calculate_total_when_both_parts_ready(db, test_engine):
    await _seed_score(db, test_engine)
    await record_score(db, schedule_id=1, student_id="S2024001", score=80, score_type="平时")
    await record_score(db, schedule_id=1, student_id="S2024001", score=90, score_type="期末")
    await db.flush()
    calculated = await auto_calculate_total_if_ready(db, 1)
    assert calculated == 1
    totals = (await db.execute(
        select(Score).where(Score.score_type == ScoreType.total)
    )).scalars().all()
    assert len(totals) == 1


@pytest.mark.asyncio
async def test_manual_score_endpoint_regression(client, db, test_engine):
    from app.deps import get_current_user
    from app.main import app

    await _seed_score(db, test_engine)
    app.dependency_overrides[get_current_user] = lambda: {
        "username": "T10001", "role": "teacher", "role_id": "T10001",
    }
    try:
        resp = await client.post("/scores/manual", json={
            "schedule_id": 1,
            "score_type": "期末",
            "scores": [{"student_id": "S2024001", "score": 87}],
        })
        assert resp.status_code == 200, resp.text
        assert resp.json()["inserted"] == 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)
