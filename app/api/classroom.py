"""
教室接口：查询空闲教室 + 预约管理
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import Schedule, Classroom, ClassroomReservation, Subject, Teacher
from app.utils.week_parser import is_week_matched
from app.utils.period_parser import is_period_overlap
from app.schemas.classroom import (
    ClassroomItem, ClassroomAvailableResponse, ClassroomAvailabilityResponse, OccupiedDetail,
)
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/classrooms", tags=["教室"])


@router.get("/available", response_model=ClassroomAvailableResponse, summary="查询空闲教室")
async def available_classrooms(
    week: int = Query(..., ge=1, le=52, description="周次，1-52"),
    day_of_week: int = Query(..., ge=1, le=7, description="星期几，1=周一"),
    period: str = Query(..., min_length=1, description="节次，如 1-2"),
    min_capacity: int = Query(0, ge=0, description="最小容纳人数"),
    building: str | None = Query(None, description="教学楼名称（可选）"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    all_schedules = await db.execute(
        select(Schedule).where(Schedule.day_of_week == day_of_week)
    )
    scheduled_ids: set[int] = set()
    for s in all_schedules.scalars().all():
        if is_week_matched(week, s.weeks) and is_period_overlap(period, s.period):
            scheduled_ids.add(s.classroom_id)

    # 同时排除已预约的教室
    reserved = await db.execute(
        select(ClassroomReservation).where(
            ClassroomReservation.week == week,
            ClassroomReservation.day_of_week == day_of_week,
            ClassroomReservation.period == period,
            ClassroomReservation.status == "已预约",
        )
    )
    reserved_ids: set[int] = {r.classroom_id for r in reserved.scalars().all()}

    occupied_ids = scheduled_ids | reserved_ids

    query = select(Classroom)
    if occupied_ids:
        query = query.where(Classroom.id.not_in(occupied_ids))
    if min_capacity > 0:
        query = query.where(Classroom.capacity >= min_capacity)
    if building:
        query = query.where(Classroom.building == building)

    result = await db.execute(query)
    classrooms = result.scalars().all()

    return ClassroomAvailableResponse(classrooms=[
        ClassroomItem(
            id=c.id, name=c.name, capacity=c.capacity,
            building=c.building, has_projector=c.has_projector,
        ) for c in classrooms
    ])


@router.get("/{classroom_id}/availability", response_model=ClassroomAvailabilityResponse, summary="教室空闲详情")
async def classroom_availability(
    classroom_id: int, week: int = Query(..., ge=1, le=52),
    day_of_week: int = Query(..., ge=1, le=7), period: str = Query(..., min_length=1),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cr_result = await db.execute(select(Classroom).where(Classroom.id == classroom_id))
    classroom = cr_result.scalar_one_or_none()
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教室不存在")

    result = await db.execute(
        select(Schedule, Subject, Teacher)
        .join(Subject, Schedule.subject_id == Subject.id)
        .join(Teacher, Schedule.teacher_id == Teacher.id)
        .where(Schedule.classroom_id == classroom_id, Schedule.day_of_week == day_of_week)
    )
    for s, subj, t in result.all():
        if is_week_matched(week, s.weeks) and is_period_overlap(period, s.period):
            return ClassroomAvailabilityResponse(
                available=False,
                classroom=ClassroomItem(id=classroom.id, name=classroom.name, capacity=classroom.capacity, building=classroom.building, has_projector=classroom.has_projector),
                occupied_by=OccupiedDetail(course_name=subj.name, teacher_name=t.name, weeks=s.weeks, day_of_week=s.day_of_week, period=s.period),
            )

    return ClassroomAvailabilityResponse(
        available=True,
        classroom=ClassroomItem(id=classroom.id, name=classroom.name, capacity=classroom.capacity, building=classroom.building, has_projector=classroom.has_projector),
    )


@router.post("/reserve", summary="预约教室")
async def reserve_classroom(
    classroom_id: int = Query(..., description="教室ID"),
    week: int = Query(..., ge=1, le=52),
    day_of_week: int = Query(..., ge=1, le=7),
    period: str = Query(..., min_length=1),
    reason: str = Query(..., min_length=1, max_length=200),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 检查教室是否存在
    cr = await db.execute(select(Classroom).where(Classroom.id == classroom_id))
    if not cr.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教室不存在")

    # 检查是否已被课程占用
    all_schedules = await db.execute(
        select(Schedule).where(Schedule.classroom_id == classroom_id, Schedule.day_of_week == day_of_week)
    )
    for s in all_schedules.scalars().all():
        if is_week_matched(week, s.weeks) and is_period_overlap(period, s.period):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该时段有课程安排，无法预约")

    # 原子预约：直接 INSERT，依赖 DB UNIQUE 约束防止竞态
    try:
        reservation = ClassroomReservation(
            classroom_id=classroom_id, week=week, day_of_week=day_of_week,
            period=period, user_id=current_user["username"],
            user_role=current_user["role"], reason=reason, status="已预约",
        )
        db.add(reservation)
        await db.commit()
        await db.refresh(reservation)
        return {"message": "预约成功", "id": reservation.id}
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该时段已被其他人预约")


@router.get("/my-reservations", summary="我的预约列表")
async def my_reservations(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ClassroomReservation, Classroom)
        .join(Classroom, ClassroomReservation.classroom_id == Classroom.id)
        .where(ClassroomReservation.user_id == current_user["username"])
        .order_by(ClassroomReservation.created_at.desc())
    )
    items = []
    for r, c in result.all():
        items.append({
            "id": r.id, "classroom_id": r.classroom_id, "classroom_name": c.name,
            "week": r.week, "day_of_week": r.day_of_week, "period": r.period,
            "reason": r.reason, "status": r.status,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
        })
    return {"reservations": items}


@router.put("/reservation/{id}/cancel", summary="取消预约")
async def cancel_reservation(
    id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ClassroomReservation).where(
            ClassroomReservation.id == id,
            ClassroomReservation.user_id == current_user["username"],
            ClassroomReservation.status == "已预约",
        )
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="预约不存在或已取消")
    await db.delete(r)
    await db.commit()
    return {"message": "已取消预约"}
