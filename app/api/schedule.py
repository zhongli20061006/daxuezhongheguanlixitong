"""
课表接口
GET    /schedule/my                — 学生：我的课表（必修+已选）
GET    /schedule/class/{class_id}  — 教师/管理员：班级课表
POST   /schedule                   — 管理员：创建课表
PUT    /schedule/{id}              — 管理员：修改课表
DELETE /schedule/{id}              — 管理员：删除课表
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import (
    Schedule, Subject, SubjectType, Teacher, Classroom, Student,
    CourseSelection, CourseCapacity, Score,
)
from app.schemas.schedule import (
    ScheduleItem, ScheduleListResponse,
    ScheduleCreateRequest, ScheduleUpdateRequest,
)

router = APIRouter(prefix="/schedule", tags=["课表"])


@router.get("/my", response_model=ScheduleListResponse, summary="我的课表")
async def my_schedule(
    current_user: dict = Depends(require_role("student")),
    db: AsyncSession = Depends(get_db),
):
    """
    学生课表：必修课（按班级自动分配）+ 已选课程（来自 course_selection）
    """
    student_id = current_user["username"]

    # 获取学生的班级ID
    stu_result = await db.execute(
        select(Student).where(Student.id == student_id)
    )
    student = stu_result.scalar_one_or_none()
    if not student or not student.class_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学生信息不完整")

    class_id = student.class_id

    # 1. 查询必修课（按班级 + 必修类型）
    compulsory_result = await db.execute(
        select(Schedule, Subject, Teacher, Classroom)
        .join(Subject, Schedule.subject_id == Subject.id)
        .join(Teacher, Schedule.teacher_id == Teacher.id)
        .join(Classroom, Schedule.classroom_id == Classroom.id)
        .where(
            Schedule.class_id == class_id,
            Subject.type == SubjectType.compulsory,
        )
    )
    courses = [
        ScheduleItem(
            id=s.id, course_name=subj.name, teacher_name=t.name,
            classroom_name=cr.name, day_of_week=s.day_of_week, period=s.period,
            weeks=s.weeks, course_type="compulsory", credit=float(subj.credit),
        )
        for s, subj, t, cr in compulsory_result.all()
    ]

    # 2. 查询已选课程（status=1）
    selected_result = await db.execute(
        select(Schedule, Subject, Teacher, Classroom)
        .join(CourseSelection, CourseSelection.schedule_id == Schedule.id)
        .join(Subject, Schedule.subject_id == Subject.id)
        .join(Teacher, Schedule.teacher_id == Teacher.id)
        .join(Classroom, Schedule.classroom_id == Classroom.id)
        .where(
            CourseSelection.student_id == student_id,
            CourseSelection.status == 1,
        )
    )
    for s, subj, t, cr in selected_result.all():
        courses.append(ScheduleItem(
            id=s.id, course_name=subj.name, teacher_name=t.name,
            classroom_name=cr.name, day_of_week=s.day_of_week, period=s.period,
            weeks=s.weeks, course_type=subj.type.value, credit=float(subj.credit),
        ))

    return ScheduleListResponse(schedules=courses)


@router.get("/class/{class_id}", response_model=ScheduleListResponse, summary="班级课表")
async def class_schedule(
    class_id: int,
    current_user: dict = Depends(require_role("teacher", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """教师/管理员查看指定班级的完整课表"""
    result = await db.execute(
        select(Schedule, Subject, Teacher, Classroom)
        .join(Subject, Schedule.subject_id == Subject.id)
        .join(Teacher, Schedule.teacher_id == Teacher.id)
        .join(Classroom, Schedule.classroom_id == Classroom.id)
        .where(Schedule.class_id == class_id)
    )
    return ScheduleListResponse(schedules=[
        ScheduleItem(
            id=s.id, course_name=subj.name, teacher_name=t.name,
            classroom_name=cr.name, day_of_week=s.day_of_week, period=s.period,
            weeks=s.weeks, course_type=subj.type.value, credit=float(subj.credit),
        )
        for s, subj, t, cr in result.all()
    ])


@router.post("", response_model=ScheduleItem, status_code=201, summary="创建课表")
async def create_schedule(
    req: ScheduleCreateRequest,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    管理员创建课表记录，同时自动创建限选/选修课的容量记录
    """
    # 校验关联记录存在
    subject_result = await db.execute(
        select(Subject).where(Subject.id == req.subject_id)
    )
    subject = subject_result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="科目不存在")

    t_result = await db.execute(select(Teacher).where(Teacher.id == req.teacher_id))
    if not t_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教师不存在")

    cr_result = await db.execute(select(Classroom).where(Classroom.id == req.classroom_id))
    if not cr_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教室不存在")

    schedule = Schedule(
        teacher_id=req.teacher_id,
        subject_id=req.subject_id,
        class_id=req.class_id,
        classroom_id=req.classroom_id,
        weeks=req.weeks,
        day_of_week=req.day_of_week,
        period=req.period,
        semester=req.semester,
    )
    db.add(schedule)
    await db.flush()

    # 限选/选修课自动创建容量记录
    if subject.type in (SubjectType.limited, SubjectType.elective):
        capacity = 50 if subject.type == SubjectType.limited else 30
        db.add(CourseCapacity(
            schedule_id=schedule.id,
            enrolled=0,
            capacity=capacity,
        ))

    await db.commit()
    await db.refresh(schedule)
    return _to_schedule_item(schedule, subject, None, None)


@router.put("/{schedule_id}", response_model=ScheduleItem, summary="修改课表")
async def update_schedule(
    schedule_id: int,
    req: ScheduleUpdateRequest,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """管理员修改课表（部分更新）"""
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课表不存在")

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(schedule, field, value)

    await db.commit()
    await db.refresh(schedule)

    # 获取关联信息
    subj_result = await db.execute(select(Subject).where(Subject.id == schedule.subject_id))
    subj = subj_result.scalar_one_or_none()
    t_result = await db.execute(select(Teacher).where(Teacher.id == schedule.teacher_id))
    t = t_result.scalar_one_or_none()
    cr_result = await db.execute(select(Classroom).where(Classroom.id == schedule.classroom_id))
    cr = cr_result.scalar_one_or_none()
    if not subj or not t or not cr:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="课表关联数据异常")

    return _to_schedule_item(schedule, subj, t, cr)


@router.delete("/{schedule_id}", summary="删除课表")
async def delete_schedule(
    schedule_id: int,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """管理员删除课表（同时删除关联的容量/选课/成绩记录）"""
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课表不存在")

    # 删除关联成绩
    score_rows = await db.execute(select(Score).where(Score.schedule_id == schedule_id))
    for sc in score_rows.scalars().all():
        await db.delete(sc)

    # 删除关联选课记录
    sel_rows = await db.execute(
        select(CourseSelection).where(CourseSelection.schedule_id == schedule_id)
    )
    for cs in sel_rows.scalars().all():
        await db.delete(cs)

    # 删除关联容量记录
    cap_result = await db.execute(
        select(CourseCapacity).where(CourseCapacity.schedule_id == schedule_id)
    )
    cap = cap_result.scalar_one_or_none()
    if cap:
        await db.delete(cap)

    await db.delete(schedule)
    await db.commit()
    return {"message": "课表已删除"}


def _to_schedule_item(s: Schedule, subj: Subject, t: Teacher | None, cr: Classroom | None) -> ScheduleItem:
    return ScheduleItem(
        id=s.id,
        course_name=subj.name,
        teacher_name=t.name if t else "",
        classroom_name=cr.name if cr else "",
        day_of_week=s.day_of_week,
        period=s.period,
        weeks=s.weeks,
        course_type=subj.type.value,
        credit=float(subj.credit),
    )
