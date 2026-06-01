"""
教室查询接口
GET /classrooms/available         — 查询空闲教室列表
GET /classrooms/{id}/availability — 查询单间教室指定时间是否空闲
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import Schedule, Classroom, Subject, Teacher
from app.utils.week_parser import is_week_matched
from app.utils.period_parser import is_period_overlap
from app.schemas.classroom import (
    ClassroomItem, ClassroomAvailableResponse, ClassroomAvailabilityResponse, OccupiedDetail,
)

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
    """
    查询指定时间段空闲的教室
    逻辑：
    1. 查出该时间段被占用的教室ID
    2. 从 classroom 表排除这些ID，并应用容量和教学楼筛选
    """
    # Step 1: 查出所有课表记录（非特定日期，比较周次和节次）
    all_schedules = await db.execute(
        select(Schedule).where(Schedule.day_of_week == day_of_week)
    )
    schedules = all_schedules.scalars().all()

    # 筛选出时间重叠的课表 → 获取被占用的教室ID列表
    occupied_ids: set[int] = set()
    for s in schedules:
        if is_week_matched(week, s.weeks) and is_period_overlap(period, s.period):
            occupied_ids.add(s.classroom_id)

    # Step 2: 查询空闲教室
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
        )
        for c in classrooms
    ])


@router.get("/{classroom_id}/availability", response_model=ClassroomAvailabilityResponse, summary="教室空闲详情")
async def classroom_availability(
    classroom_id: int,
    week: int = Query(..., ge=1, le=52),
    day_of_week: int = Query(..., ge=1, le=7),
    period: str = Query(..., min_length=1),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    查询单间教室在指定时间是否空闲
    如果被占用，返回占用的课程信息
    """
    # 查询教室是否存在
    cr_result = await db.execute(
        select(Classroom).where(Classroom.id == classroom_id)
    )
    classroom = cr_result.scalar_one_or_none()
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教室不存在")

    # 查询该时间段内该教室的课表
    result = await db.execute(
        select(Schedule, Subject, Teacher)
        .join(Subject, Schedule.subject_id == Subject.id)
        .join(Teacher, Schedule.teacher_id == Teacher.id)
        .where(
            Schedule.classroom_id == classroom_id,
            Schedule.day_of_week == day_of_week,
        )
    )
    rows = result.all()

    # 检查是否有时间重叠的课程
    for s, subj, t in rows:
        if is_week_matched(week, s.weeks) and is_period_overlap(period, s.period):
            return ClassroomAvailabilityResponse(
                available=False,
                classroom=ClassroomItem(
                    id=classroom.id, name=classroom.name,
                    capacity=classroom.capacity, building=classroom.building,
                    has_projector=classroom.has_projector,
                ),
                occupied_by=OccupiedDetail(
                    course_name=subj.name,
                    teacher_name=t.name,
                    weeks=s.weeks,
                    day_of_week=s.day_of_week,
                    period=s.period,
                ),
            )

    return ClassroomAvailabilityResponse(
        available=True,
        classroom=ClassroomItem(
            id=classroom.id, name=classroom.name,
            capacity=classroom.capacity, building=classroom.building,
            has_projector=classroom.has_projector,
        ),
    )
