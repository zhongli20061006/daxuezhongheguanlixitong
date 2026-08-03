"""培养方案接口回归：agent01 单方案正常返回、重复方案不 500、已获学分统计正确。"""
import pytest

from app.models import (
    PlanCourse, Schedule, Score, ScoreType, Student, StudentClass, Subject,
    SubjectType, TrainingPlan,
)


async def _cleanup(test_engine):
    from sqlalchemy import delete as sa_delete

    async with test_engine.begin() as conn:
        for model in (
            Score, PlanCourse, TrainingPlan, Schedule, Subject,
            Student, StudentClass,
        ):
            await conn.execute(sa_delete(model))


def _auth_agent01(app):
    from app.deps import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {
        "username": "agent01", "role": "student", "role_id": "agent01",
    }
    return get_current_user


async def _seed_basic(db, test_engine, plan_count: int = 1):
    await _cleanup(test_engine)
    db.add(StudentClass(id=1, name="2024级计算机科学1班", major="计算机科学与技术", grade=2024, advisor_id=1))
    db.add(Student(id="agent01", name="智能体测试员", class_id=1))
    db.add(Subject(id=1, name="高等数学", credit=5.0, type=SubjectType.compulsory))
    db.add(Schedule(
        id=1, teacher_id=1, subject_id=1, class_id=1, classroom_id=1,
        weeks="1-18", day_of_week=1, period="1-2", semester="2024-2025-1",
    ))
    plans = []
    for i in range(plan_count):
        plan = TrainingPlan(
            major="计算机科学与技术", grade=2024,
            total_credits_required=170, elective_credits_required=20,
        )
        db.add(plan)
        plans.append(plan)
    await db.flush()
    db.add(PlanCourse(plan_id=plans[0].id, subject_id=1, course_type="compulsory", credit=5.0))
    db.add(Score(
        student_id="agent01", schedule_id=1, score=90, gpa=4.0,
        score_type=ScoreType.total, attempt=1,
    ))
    await db.commit()
    return plans[0].id


@pytest.mark.asyncio
async def test_agent01_my_plan_returns_plan_and_credits(client, db, test_engine):
    from app.main import app

    plan_id = await _seed_basic(db, test_engine)
    key = _auth_agent01(app)
    try:
        resp = await client.get("/training-plan/my")
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan"]["id"] == plan_id
        assert data["plan"]["total_credits_earned"] == 5.0  # 已通过课程学分不再显示 0
        assert data["courses"][0]["status"] == "已通过"
    finally:
        app.dependency_overrides.pop(key, None)


@pytest.mark.asyncio
async def test_my_plan_duplicate_plans_does_not_500(client, db, test_engine):
    """库里同专业同年级存在重复方案时，取 id 最小的一条，而不是抛 500。"""
    from app.main import app

    first_id = await _seed_basic(db, test_engine, plan_count=2)
    key = _auth_agent01(app)
    try:
        resp = await client.get("/training-plan/my")
        assert resp.status_code == 200
        assert resp.json()["plan"]["id"] == first_id
    finally:
        app.dependency_overrides.pop(key, None)
