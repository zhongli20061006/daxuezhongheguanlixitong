"""
培养方案接口
POST /training-plan/plans          — 创建培养方案
GET  /training-plan/plans          — 查询培养方案列表
GET  /training-plan/plans/{id}/courses  — 方案课程列表
POST /training-plan/courses        — 添加方案课程
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models.training_plan import TrainingPlan
from app.models.plan_course import PlanCourse
from app.models.subject import Subject
from app.schemas.training import (
    TrainingPlanCreate, PlanCourseCreate,
    PlanItem, PlanListResponse,
    PlanCourseItem, PlanCourseListResponse,
)

router = APIRouter(prefix="/training-plan", tags=["培养方案"])


@router.post("/plans", summary="创建培养方案")
async def create_plan(
    req: TrainingPlanCreate,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(TrainingPlan).where(
            TrainingPlan.major == req.major,
            TrainingPlan.grade == req.grade,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该专业年级的培养方案已存在")

    plan = TrainingPlan(
        major=req.major, grade=req.grade,
        total_credits_required=req.total_credits_required,
        elective_credits_required=req.elective_credits_required,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return {"message": "培养方案已创建", "id": plan.id}


@router.get("/plans", response_model=PlanListResponse, summary="培养方案列表")
async def list_plans(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TrainingPlan).order_by(TrainingPlan.grade.desc(), TrainingPlan.major))
    plans = result.scalars().all()
    return PlanListResponse(plans=[
        PlanItem(
            id=p.id, major=p.major, grade=p.grade,
            total_credits_required=float(p.total_credits_required),
            elective_credits_required=float(p.elective_credits_required),
        ) for p in plans
    ])


@router.get("/plans/{plan_id}/courses", response_model=PlanCourseListResponse, summary="方案课程列表")
async def plan_courses(
    plan_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlanCourse, Subject)
        .join(Subject, PlanCourse.subject_id == Subject.id)
        .where(PlanCourse.plan_id == plan_id)
    )
    rows = result.all()
    return PlanCourseListResponse(courses=[
        PlanCourseItem(
            id=pc.id, plan_id=pc.plan_id, subject_id=pc.subject_id,
            subject_name=subj.name, course_type=pc.course_type,
            limited_group=pc.limited_group, min_required=pc.min_required,
            credit=float(pc.credit),
        ) for pc, subj in rows
    ])


@router.post("/courses", summary="添加方案课程")
async def add_plan_course(
    req: PlanCourseCreate,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    # 验证方案存在
    plan_result = await db.execute(select(TrainingPlan).where(TrainingPlan.id == req.plan_id))
    if not plan_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="培养方案不存在")
    # 验证科目存在
    subj_result = await db.execute(select(Subject).where(Subject.id == req.subject_id))
    if not subj_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="科目不存在")

    pc = PlanCourse(
        plan_id=req.plan_id, subject_id=req.subject_id,
        course_type=req.course_type, limited_group=req.limited_group,
        min_required=req.min_required, credit=req.credit,
    )
    db.add(pc)
    await db.commit()
    return {"message": "方案课程已添加", "id": pc.id}
