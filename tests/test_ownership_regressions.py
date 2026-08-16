"""数据归属回归测试（2026-08-14 残余越权收口批次）。

覆盖：
- B6 成绩查看水平越权：教师只能查看本人授课课程的成绩，staff 无权限
- B7 请假详情水平越权：仅学生本人/本班辅导员/学院管理员/admin 可见
- B8 通知归属：单条已读只能操作自己可见的通知；清理仅作用于自己的已读记录（admin 保留全局）
"""
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import delete as sa_delete, select

from app.models import (
    Classroom, LeaveApplication, Notification, NotificationUser,
    Schedule, Score, ScoreType, Student, StudentClass, Subject,
    SubjectType, Teacher,
)


async def _cleanup(test_engine):
    async with test_engine.begin() as conn:
        for model in (
            NotificationUser, Notification, LeaveApplication,
            Score, Schedule, Student, Classroom, Subject, Teacher, StudentClass,
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


# ─────────────────────────── B6 成绩查看 ───────────────────────────

async def _seed_score_context(db, test_engine):
    """种子：教师A(授课程A)、教师B(授课程B)、学生S2024001 两门课均有成绩。"""
    await _cleanup(test_engine)
    db.add_all([
        StudentClass(id=1, name="一班", major="计算机", grade=2024, advisor_id=1),
        Teacher(id=1, name="教师A", job_number="T10001", department="计算机", is_college_admin=False),
        Teacher(id=2, name="教师B", job_number="T10002", department="计算机", is_college_admin=False),
        Subject(id=1, name="课程A", credit=2.0, type=SubjectType.elective),
        Subject(id=2, name="课程B", credit=2.0, type=SubjectType.elective),
        Classroom(id=1, name="D101", capacity=60, building="D", has_projector=False),
        Student(id="S2024001", name="学生甲", class_id=1),
        Schedule(
            id=1, teacher_id=1, subject_id=1, class_id=1, classroom_id=1,
            weeks="1-18", day_of_week=1, period="1-2", semester="2024-2025-1",
        ),
        Schedule(
            id=2, teacher_id=2, subject_id=2, class_id=1, classroom_id=1,
            weeks="1-18", day_of_week=1, period="1-2", semester="2024-2025-1",
        ),
        Score(student_id="S2024001", schedule_id=1, score=90.0, gpa=5.0, score_type=ScoreType.daily, attempt=1),
        Score(student_id="S2024001", schedule_id=2, score=80.0, gpa=4.0, score_type=ScoreType.daily, attempt=1),
    ])
    await db.commit()


@pytest.mark.asyncio
async def test_teacher_sees_only_own_course_scores(client, db, test_engine):
    """B6：教师A查看学生成绩时只应看到课程A（本人授课），看不到课程B。"""
    from app.main import app

    await _seed_score_context(db, test_engine)
    _set_role(app, "T10001", "teacher", "T10001")
    try:
        r = await client.get("/scores/student/S2024001")
        assert r.status_code == 200, r.text
        courses = {s["course_name"] for s in r.json()["scores"]}
        assert "课程A" in courses
        assert "课程B" not in courses
    finally:
        _clear_role(app)


@pytest.mark.asyncio
async def test_staff_cannot_view_student_scores(client, db, test_engine):
    """B6：staff（后勤）查看任何学生成绩必须 403。"""
    from app.main import app

    await _seed_score_context(db, test_engine)
    _set_role(app, "S0001", "staff", "S0001")
    try:
        r = await client.get("/scores/student/S2024001")
        assert r.status_code == 403, r.text
    finally:
        _clear_role(app)


@pytest.mark.asyncio
async def test_admin_can_view_all_student_scores(client, db, test_engine):
    """B6：admin 保留全量查看（两门课都应返回）。"""
    from app.main import app

    await _seed_score_context(db, test_engine)
    _set_role(app, "admin", "admin", "admin")
    try:
        r = await client.get("/scores/student/S2024001")
        assert r.status_code == 200, r.text
        courses = {s["course_name"] for s in r.json()["scores"]}
        assert courses == {"课程A", "课程B"}
    finally:
        _clear_role(app)


# ─────────────────────────── B7 请假详情 ───────────────────────────

async def _seed_leave_detail_context(db, test_engine):
    """种子：一班(辅导员T10001)、二班(辅导员T10002)、普通教师T10003、学院管理员T10004。"""
    await _cleanup(test_engine)
    db.add_all([
        StudentClass(id=1, name="一班", major="计算机", grade=2024, advisor_id=1),
        StudentClass(id=2, name="二班", major="计算机", grade=2024, advisor_id=2),
        Teacher(id=1, name="一班辅导员", job_number="T10001", department="计算机", is_college_admin=False),
        Teacher(id=2, name="二班辅导员", job_number="T10002", department="计算机", is_college_admin=False),
        Teacher(id=3, name="普通授课教师", job_number="T10003", department="计算机", is_college_admin=False),
        Teacher(id=4, name="学院管理员", job_number="T10004", department="计算机", is_college_admin=True),
        Student(id="S2024001", name="一班学生", class_id=1),
        Student(id="S2024002", name="二班学生", class_id=2),
        LeaveApplication(
            id=1, student_id="S2024001",
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=1),
            total_days=1, reason="感冒", status="审批中(辅导员)",
        ),
    ])
    await db.commit()


@pytest.mark.asyncio
async def test_student_cannot_view_others_leave_detail(client, db, test_engine):
    """B7：学生查看他人请假详情必须 403。"""
    from app.main import app

    await _seed_leave_detail_context(db, test_engine)
    _set_role(app, "S2024002", "student", "S2024002")
    try:
        r = await client.get("/leave/1/detail")
        assert r.status_code == 403, r.text
    finally:
        _clear_role(app)


@pytest.mark.asyncio
async def test_other_class_advisor_cannot_view_leave_detail(client, db, test_engine):
    """B7：非本班辅导员查看请假详情必须 403。"""
    from app.main import app

    await _seed_leave_detail_context(db, test_engine)
    _set_role(app, "T10002", "teacher", "T10002")
    try:
        r = await client.get("/leave/1/detail")
        assert r.status_code == 403, r.text
    finally:
        _clear_role(app)


@pytest.mark.asyncio
async def test_own_class_advisor_can_view_leave_detail(client, db, test_engine):
    """B7：本班辅导员查看本班学生请假详情应 200。"""
    from app.main import app

    await _seed_leave_detail_context(db, test_engine)
    _set_role(app, "T10001", "teacher", "T10001")
    try:
        r = await client.get("/leave/1/detail")
        assert r.status_code == 200, r.text
        assert r.json()["leave"]["student_id"] == "S2024001"
    finally:
        _clear_role(app)


@pytest.mark.asyncio
async def test_plain_teacher_cannot_view_leave_detail(client, db, test_engine):
    """B7：普通授课教师（非辅导员/学院管理员）查看请假详情必须 403。"""
    from app.main import app

    await _seed_leave_detail_context(db, test_engine)
    _set_role(app, "T10003", "teacher", "T10003")
    try:
        r = await client.get("/leave/1/detail")
        assert r.status_code == 403, r.text
    finally:
        _clear_role(app)


@pytest.mark.asyncio
async def test_college_admin_can_view_leave_detail(client, db, test_engine):
    """B7：学院管理员查看请假详情应 200。"""
    from app.main import app

    await _seed_leave_detail_context(db, test_engine)
    _set_role(app, "T10004", "teacher", "T10004")
    try:
        r = await client.get("/leave/1/detail")
        assert r.status_code == 200, r.text
    finally:
        _clear_role(app)


@pytest.mark.asyncio
async def test_admin_can_view_leave_detail(client, db, test_engine):
    """B7：admin 查看请假详情应 200。"""
    from app.main import app

    await _seed_leave_detail_context(db, test_engine)
    _set_role(app, "admin", "admin", "admin")
    try:
        r = await client.get("/leave/1/detail")
        assert r.status_code == 200, r.text
    finally:
        _clear_role(app)


# ─────────────────────────── B8 通知归属 ───────────────────────────

async def _seed_notification_context(db, test_engine):
    """种子：n1(定向A,已读)、n2(定向B,已读)、n3(全局,未读)。"""
    await _cleanup(test_engine)
    db.add_all([
        Notification(id=1, title="给A的通知", content="内容A", event_type="test"),
        Notification(id=2, title="给B的通知", content="内容B", event_type="test"),
        Notification(id=3, title="全局通知", content="内容C", event_type="test"),
        NotificationUser(notification_id=1, recipient_id="S2024001", recipient_role=None, is_read=True),
        NotificationUser(notification_id=2, recipient_id="S2024002", recipient_role=None, is_read=True),
        NotificationUser(notification_id=3, recipient_id=None, recipient_role=None, is_read=False),
    ])
    await db.commit()


@pytest.mark.asyncio
async def test_mark_read_other_users_notification_rejected(client, db, test_engine):
    """B8：用户A把只发给B的定向通知标记已读必须 404。"""
    from app.main import app

    await _seed_notification_context(db, test_engine)
    _set_role(app, "S2024001", "student", "S2024001")
    try:
        r = await client.post("/notification/2/read")
        assert r.status_code == 404, r.text
    finally:
        _clear_role(app)
    # B 的已读状态不应被改动
    row = (await db.execute(
        select(NotificationUser).where(NotificationUser.notification_id == 2)
    )).scalar_one()
    assert row.is_read is True


@pytest.mark.asyncio
async def test_mark_read_own_notification_ok(client, db, test_engine):
    """B8：用户A标记自己可见的通知应 200 且状态生效。"""
    from app.main import app

    await _seed_notification_context(db, test_engine)
    _set_role(app, "S2024001", "student", "S2024001")
    try:
        r = await client.post("/notification/3/read")
        assert r.status_code == 200, r.text
    finally:
        _clear_role(app)
    row = (await db.execute(
        select(NotificationUser).where(NotificationUser.notification_id == 3)
    )).scalar_one()
    assert row.is_read is True


@pytest.mark.asyncio
async def test_cleanup_only_own_read_notifications(client, db, test_engine):
    """B8：普通用户清理已读只应删除自己的记录，不影响其他用户。"""
    from app.main import app

    await _seed_notification_context(db, test_engine)
    _set_role(app, "S2024001", "student", "S2024001")
    try:
        r = await client.post("/notification/cleanup", params={"days": 0})
        assert r.status_code == 200, r.text
    finally:
        _clear_role(app)

    # 用户A自己的已读通知(n1)行被删除，n1 成为孤儿后 Notification 本体也被删除
    n1_rows = (await db.execute(
        select(NotificationUser).where(NotificationUser.notification_id == 1)
    )).scalars().all()
    assert n1_rows == []
    n1 = (await db.execute(
        select(Notification).where(Notification.id == 1)
    )).scalar_one_or_none()
    assert n1 is None
    # 用户B的已读通知(n2)必须原样保留
    n2_rows = (await db.execute(
        select(NotificationUser).where(NotificationUser.notification_id == 2)
    )).scalars().all()
    assert len(n2_rows) == 1
    assert n2_rows[0].recipient_id == "S2024002"
    assert n2_rows[0].is_read is True
    # 全局未读通知(n3)不受影响
    n3 = (await db.execute(
        select(NotificationUser).where(NotificationUser.notification_id == 3)
    )).scalar_one()
    assert n3.is_read is False


@pytest.mark.asyncio
async def test_admin_cleanup_keeps_global_semantics(client, db, test_engine):
    """B8：admin 清理保留全局语义——所有已读通知行被删除。"""
    from app.main import app

    await _seed_notification_context(db, test_engine)
    _set_role(app, "admin", "admin", "admin")
    try:
        r = await client.post("/notification/cleanup", params={"days": 0})
        assert r.status_code == 200, r.text
        assert r.json()["deleted"] >= 2
    finally:
        _clear_role(app)

    remaining = (await db.execute(
        select(NotificationUser).where(NotificationUser.is_read == True)
    )).scalars().all()
    assert remaining == []
