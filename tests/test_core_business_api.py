"""核心业务 API 回归：选课（CAS 防超选）、退课、请假审批流、自动排考、毕业审核。"""
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models import (
    Classroom, CourseCapacity, CourseSelection, LeaveApplication, PlanCourse,
    Schedule, Student, StudentClass, Subject, SubjectType, SystemConfig,
    Teacher, TrainingPlan,
)


async def _cleanup(test_engine):
    from sqlalchemy import delete as sa_delete

    from app.models import (
        ApprovalConfig, ApprovalRecord, ClassroomReservation, Exam, ExamArrangement,
        ExamStudent, GraduationAudit, Notification, NotificationUser, Repair, Score,
    )

    async with test_engine.begin() as conn:
        for model in (
            NotificationUser, Notification, ApprovalRecord, LeaveApplication,
            ApprovalConfig, ClassroomReservation, Repair, GraduationAudit,
            ExamStudent, ExamArrangement, Exam, Score,
            CourseSelection, CourseCapacity, Schedule, SystemConfig,
            PlanCourse, TrainingPlan, Student, Classroom, Subject, Teacher, StudentClass,
        ):
            await conn.execute(sa_delete(model))


def _set_role(app, username, role, role_id):
    from app.deps import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {
        "username": username, "role": role, "role_id": role_id,
    }


def _clear_role(app):
    from app.deps import get_current_user

    app.dependency_overrides.pop(get_current_user, None)


async def _seed_selection(db, test_engine, capacity=1, enrolled=0):
    await _cleanup(test_engine)
    db.add_all([
        StudentClass(id=1, name="测试班", major="计算机", grade=2024, advisor_id=1),
        Teacher(id=1, name="张老师", job_number="T10001", department="计算机", title="教授", is_college_admin=False),
        Subject(id=1, name="人工智能实战", credit=2.0, type=SubjectType.elective),
        Classroom(id=1, name="D101", capacity=60, building="D", has_projector=False),
        Student(id="S2024001", name="测试学生一", class_id=1),
        Student(id="S2024002", name="测试学生二", class_id=1),
        SystemConfig(config_key="selection_start_time", config_value="2020-01-01 08:00:00"),
        SystemConfig(config_key="selection_end_time", config_value="2099-12-31 18:00:00"),
    ])
    await db.flush()
    db.add(Schedule(
        id=1, teacher_id=1, subject_id=1, class_id=1, classroom_id=1,
        weeks="1-18", day_of_week=1, period="1-2", semester="2024-2025-1",
    ))
    db.add(CourseCapacity(schedule_id=1, enrolled=enrolled, capacity=capacity))
    await db.commit()


@pytest.mark.asyncio
async def test_selection_enroll_then_drop(client, db, test_engine):
    from app.main import app

    await _seed_selection(db, test_engine, capacity=1, enrolled=0)
    _set_role(app, "S2024001", "student", "S2024001")
    try:
        r = await client.post("/selection/enroll", params={"schedule_id": 1})
        assert r.status_code == 200, r.text
        enrolled = (await db.execute(
            select(CourseCapacity.enrolled).where(CourseCapacity.schedule_id == 1)
        )).scalar_one()
        assert enrolled == 1

        mine = await client.get("/selection/my-courses")
        assert mine.status_code == 200
        assert mine.json()["courses"]

        r2 = await client.post("/selection/drop", params={"schedule_id": 1})
        assert r2.status_code == 200, r2.text
        enrolled = (await db.execute(
            select(CourseCapacity.enrolled).where(CourseCapacity.schedule_id == 1)
        )).scalar_one()
        assert enrolled == 0

        r3 = await client.post("/selection/drop", params={"schedule_id": 1})
        assert r3.status_code == 404
    finally:
        _clear_role(app)


@pytest.mark.asyncio
async def test_selection_enroll_duplicate_conflict(client, db, test_engine):
    from app.main import app

    await _seed_selection(db, test_engine, capacity=1, enrolled=0)
    _set_role(app, "S2024001", "student", "S2024001")
    try:
        r1 = await client.post("/selection/enroll", params={"schedule_id": 1})
        assert r1.status_code == 200, r1.text
        r2 = await client.post("/selection/enroll", params={"schedule_id": 1})
        assert r2.status_code == 409
        assert "重复选课" in r2.json()["detail"]
    finally:
        _clear_role(app)


@pytest.mark.asyncio
async def test_selection_enroll_capacity_full_cas(client, db, test_engine):
    from app.main import app

    await _seed_selection(db, test_engine, capacity=1, enrolled=1)
    _set_role(app, "S2024002", "student", "S2024002")
    try:
        r = await client.post("/selection/enroll", params={"schedule_id": 1})
        assert r.status_code == 409
        assert "课程已满" in r.json()["detail"]
        enrolled = (await db.execute(
            select(CourseCapacity.enrolled).where(CourseCapacity.schedule_id == 1)
        )).scalar_one()
        assert enrolled == 1
    finally:
        _clear_role(app)


async def _seed_leave(db, test_engine):
    await _cleanup(test_engine)
    db.add_all([
        StudentClass(id=1, name="测试班", major="计算机", grade=2024, advisor_id=1),
        Teacher(id=1, name="张老师", job_number="T10001", department="计算机", title="教授", is_college_admin=False),
        Student(id="S2024001", name="测试学生一", class_id=1),
    ])
    await db.commit()


@pytest.mark.asyncio
async def test_leave_apply_and_advisor_approve(client, db, test_engine):
    from app.main import app

    await _seed_leave(db, test_engine)
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    _set_role(app, "S2024001", "student", "S2024001")
    try:
        r = await client.post("/leave/apply", json={
            "start_date": tomorrow, "end_date": tomorrow, "reason": "感冒",
        })
        assert r.status_code == 200, r.text
        leave_id = r.json()["id"]
    finally:
        _clear_role(app)

    _set_role(app, "T10001", "teacher", "T10001")
    try:
        rp = await client.get("/advisor/pending-approvals")
        assert rp.status_code == 200
        assert any(l["id"] == leave_id for l in rp.json()["leaves"])

        ra = await client.post("/advisor/approve", json={
            "leave_id": leave_id, "result": "通过", "comment": "同意",
        })
        assert ra.status_code == 200, ra.text
        leave = (await db.execute(
            select(LeaveApplication).where(LeaveApplication.id == leave_id)
        )).scalar_one()
        assert leave.status == "已通过"
    finally:
        _clear_role(app)


@pytest.mark.asyncio
async def test_exam_generate_no_courses(client, db, test_engine):
    from app.main import app

    await _cleanup(test_engine)
    _set_role(app, "admin01", "admin", "A001")
    try:
        r = await client.post("/exam/generate", json={"semester": "2024-2025-1"})
        assert r.status_code == 200, r.text
        assert r.json()["exam_count"] == 0
    finally:
        _clear_role(app)


@pytest.mark.asyncio
async def test_exam_generate_creates_exam(client, db, test_engine):
    from app.main import app

    await _cleanup(test_engine)
    db.add_all([
        StudentClass(id=1, name="测试班", major="计算机", grade=2024, advisor_id=1),
        Teacher(id=1, name="张老师", job_number="T10001", department="计算机", title="教授", is_college_admin=False),
        Subject(id=1, name="高等数学", credit=5.0, type=SubjectType.compulsory),
        Classroom(id=1, name="D101", capacity=60, building="D", has_projector=False),
        Student(id="S2024001", name="测试学生一", class_id=1),
    ])
    await db.flush()
    db.add(Schedule(
        id=1, teacher_id=1, subject_id=1, class_id=1, classroom_id=1,
        weeks="1-18", day_of_week=1, period="1-2", semester="2024-2025-1",
    ))
    db.add(CourseSelection(student_id="S2024001", schedule_id=1, status=1))
    await db.commit()
    _set_role(app, "admin01", "admin", "A001")
    try:
        r = await client.post("/exam/generate", json={"semester": "2024-2025-1"})
        assert r.status_code == 200, r.text
        assert r.json()["exam_count"] >= 1
    finally:
        _clear_role(app)


@pytest.mark.asyncio
async def test_graduation_audit_insufficient_credits(client, db, test_engine):
    from app.main import app

    await _cleanup(test_engine)
    db.add_all([
        StudentClass(id=1, name="测试班", major="计算机科学与技术", grade=2024, advisor_id=1),
        Teacher(id=1, name="张老师", job_number="T10001", department="计算机", title="教授", is_college_admin=False),
        Subject(id=1, name="高等数学", credit=5.0, type=SubjectType.compulsory),
        Student(id="S2024001", name="测试学生一", class_id=1),
    ])
    await db.flush()
    db.add(TrainingPlan(
        major="计算机科学与技术", grade=2024,
        total_credits_required=170, elective_credits_required=20,
    ))
    await db.flush()
    plan = (await db.execute(select(TrainingPlan))).scalar_one()
    db.add(PlanCourse(plan_id=plan.id, subject_id=1, course_type="compulsory", credit=5.0))
    await db.commit()

    _set_role(app, "admin01", "admin", "A001")
    try:
        r = await client.post("/graduation/audit/S2024001")
        assert r.status_code == 200, r.text
        assert r.json()["is_graduatable"] is False
    finally:
        _clear_role(app)
