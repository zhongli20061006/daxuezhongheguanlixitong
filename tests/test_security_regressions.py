"""安全与正确性回归测试（2026-08-14 修复批次）。

覆盖：
- B1 请假审批水平越权：非本班辅导员不能审批
- B2 跨班选课：学生只能选本班课程
- B5 退课→重选→再退课：不再触发唯一键冲突（500）
"""
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import delete as sa_delete, select, text

from app.models import (
    ApprovalConfig, ApprovalRecord, Classroom, ClassroomReservation,
    CourseCapacity, CourseSelection, Exam, ExamArrangement, ExamStudent,
    GraduationAudit, LeaveApplication, Notification, NotificationUser,
    PlanCourse, Repair, Schedule, Score, Student, StudentClass, Subject,
    SubjectType, SystemConfig, Teacher, TrainingPlan,
)


async def _cleanup(test_engine):
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


async def _seed_enroll_context(db, test_engine, schedule_class_id: int):
    """种子：一班/二班 + 学生(一班) + 一门选修课课表。"""
    await _cleanup(test_engine)
    db.add_all([
        StudentClass(id=1, name="一班", major="计算机", grade=2024, advisor_id=1),
        StudentClass(id=2, name="二班", major="计算机", grade=2024, advisor_id=2),
        Teacher(id=1, name="一班辅导员", job_number="T10001", department="计算机", is_college_admin=False),
        Teacher(id=2, name="二班辅导员", job_number="T10002", department="计算机", is_college_admin=False),
        Subject(id=1, name="人工智能实战", credit=2.0, type=SubjectType.elective),
        Classroom(id=1, name="D101", capacity=60, building="D", has_projector=False),
        Student(id="S2024001", name="一班学生", class_id=1),
        SystemConfig(config_key="selection_start_time", config_value="2020-01-01 08:00:00"),
        SystemConfig(config_key="selection_end_time", config_value="2099-12-31 18:00:00"),
    ])
    await db.flush()
    db.add(Schedule(
        id=1, teacher_id=1, subject_id=1, class_id=schedule_class_id, classroom_id=1,
        weeks="1-18", day_of_week=1, period="1-2", semester="2024-2025-1",
    ))
    db.add(CourseCapacity(schedule_id=1, enrolled=0, capacity=30))
    await db.commit()


@pytest.mark.asyncio
async def test_advisor_cannot_approve_other_class_leave(client, db, test_engine):
    """B1：非本班辅导员审批必须被拒绝，本班辅导员可正常审批。"""
    from app.main import app

    await _cleanup(test_engine)
    db.add_all([
        StudentClass(id=1, name="一班", major="计算机", grade=2024, advisor_id=1),
        StudentClass(id=2, name="二班", major="计算机", grade=2024, advisor_id=2),
        Teacher(id=1, name="一班辅导员", job_number="T10001", department="计算机", is_college_admin=False),
        Teacher(id=2, name="二班辅导员", job_number="T10002", department="计算机", is_college_admin=False),
        Student(id="S2024001", name="一班学生", class_id=1),
    ])
    await db.commit()

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

    # 二班辅导员审批一班学生的请假 → 400 拒绝
    _set_role(app, "T10002", "teacher", "T10002")
    try:
        r2 = await client.post("/advisor/approve", json={
            "leave_id": leave_id, "result": "通过", "comment": "",
        })
        assert r2.status_code == 400, r2.text
        assert "无权审批" in r2.json()["detail"]
    finally:
        _clear_role(app)

    # 本班辅导员审批 → 成功
    _set_role(app, "T10001", "teacher", "T10001")
    try:
        r3 = await client.post("/advisor/approve", json={
            "leave_id": leave_id, "result": "通过", "comment": "同意",
        })
        assert r3.status_code == 200, r3.text
    finally:
        _clear_role(app)

    leave = (await db.execute(
        select(LeaveApplication).where(LeaveApplication.id == leave_id)
    )).scalar_one()
    assert leave.status == "已通过"


@pytest.mark.asyncio
async def test_enroll_cross_class_rejected(client, db, test_engine):
    """B2：学生选他班课表必须被 403 拒绝。"""
    from app.main import app

    await _seed_enroll_context(db, test_engine, schedule_class_id=2)
    _set_role(app, "S2024001", "student", "S2024001")
    try:
        r = await client.post("/selection/enroll", params={"schedule_id": 1})
        assert r.status_code == 403, r.text
        assert "不属于您所在班级" in r.json()["detail"]
    finally:
        _clear_role(app)


@pytest.mark.asyncio
async def test_drop_re_enroll_drop_roundtrip(client, db, test_engine):
    """B5：退课→重选→再退课全程 200，且只保留一条 status=0 记录。"""
    from app.main import app

    await _seed_enroll_context(db, test_engine, schedule_class_id=1)
    _set_role(app, "S2024001", "student", "S2024001")
    try:
        r1 = await client.post("/selection/enroll", params={"schedule_id": 1})
        assert r1.status_code == 200, r1.text
        r2 = await client.post("/selection/drop", params={"schedule_id": 1})
        assert r2.status_code == 200, r2.text

        # 绕过 2 分钟重选频率限制（测试环境直接回拨 cancel_time）
        await db.execute(
            text(
                "UPDATE course_selection SET cancel_time = :t "
                "WHERE student_id = :s AND schedule_id = :c"
            ),
            {"t": datetime.now() - timedelta(minutes=5), "s": "S2024001", "c": 1},
        )
        await db.commit()

        r3 = await client.post("/selection/enroll", params={"schedule_id": 1})
        assert r3.status_code == 200, r3.text
        r4 = await client.post("/selection/drop", params={"schedule_id": 1})
        assert r4.status_code == 200, r4.text
    finally:
        _clear_role(app)

    rows = (await db.execute(
        select(CourseSelection).where(
            CourseSelection.student_id == "S2024001",
            CourseSelection.schedule_id == 1,
        )
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == 0
    enrolled = (await db.execute(
        select(CourseCapacity.enrolled).where(CourseCapacity.schedule_id == 1)
    )).scalar_one()
    assert enrolled == 0


@pytest.mark.asyncio
async def test_classroom_reservation_duplicate_conflict(client, db, test_engine):
    """B3：同一教室同时段重复预约必须 409（唯一约束生效）。"""
    from app.main import app

    await _cleanup(test_engine)
    db.add(Classroom(id=1, name="D101", capacity=60, building="D", has_projector=False))
    await db.commit()

    _set_role(app, "S2024001", "student", "S2024001")
    try:
        r1 = await client.post("/classrooms/reserve", params={
            "classroom_id": 1, "week": 1, "day_of_week": 1,
            "period": "1-2", "reason": "自习",
        })
        assert r1.status_code == 200, r1.text
        r2 = await client.post("/classrooms/reserve", params={
            "classroom_id": 1, "week": 1, "day_of_week": 1,
            "period": "1-2", "reason": "自习",
        })
        assert r2.status_code == 409, r2.text
        assert "已被其他人预约" in r2.json()["detail"]
    finally:
        _clear_role(app)


@pytest.mark.asyncio
async def test_approval_record_duplicate_level_constraint(db, test_engine):
    """B4：同一请假单同级别重复审批记录被唯一约束拒绝。"""
    from sqlalchemy.exc import IntegrityError

    await _cleanup(test_engine)
    db.add(ApprovalRecord(
        leave_id=1, approver_id="T10001", approver_role="advisor",
        level=1, result="通过", comment="",
    ))
    await db.commit()
    db.add(ApprovalRecord(
        leave_id=1, approver_id="T10001", approver_role="advisor",
        level=1, result="通过", comment="",
    ))
    with pytest.raises(IntegrityError):
        await db.commit()
    await db.rollback()


@pytest.mark.asyncio
async def test_approve_invalid_result_rejected(client, db, test_engine):
    """B4：非法审批结果必须 422（枚举校验）。"""
    from app.main import app

    await _cleanup(test_engine)
    db.add_all([
        StudentClass(id=1, name="一班", major="计算机", grade=2024, advisor_id=1),
        Teacher(id=1, name="一班辅导员", job_number="T10001", department="计算机", is_college_admin=False),
        Student(id="S2024001", name="一班学生", class_id=1),
        LeaveApplication(
            student_id="S2024001",
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=1),
            total_days=1, reason="感冒", status="审批中(辅导员)",
        ),
    ])
    await db.commit()

    _set_role(app, "T10001", "teacher", "T10001")
    try:
        r = await client.post("/advisor/approve", json={
            "leave_id": 1, "result": "随便", "comment": "",
        })
        assert r.status_code == 422, r.text
    finally:
        _clear_role(app)
