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
from app.models.student import Student
from app.models.student_class import StudentClass
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
    plan_result = await db.execute(select(TrainingPlan).where(TrainingPlan.id == req.plan_id))
    if not plan_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="培养方案不存在")
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


@router.delete("/courses/{course_id}", summary="删除方案课程")
async def delete_plan_course(
    course_id: int,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PlanCourse).where(PlanCourse.id == course_id))
    pc = result.scalar_one_or_none()
    if not pc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="方案课程不存在")
    await db.delete(pc)
    await db.commit()
    return {"message": "方案课程已删除"}


@router.get("/my", summary="学生的培养方案")
async def my_plan(
    current_user: dict = Depends(require_role("student")),
    db: AsyncSession = Depends(get_db),
):
    stu_result = await db.execute(
        select(Student, StudentClass).join(StudentClass, Student.class_id == StudentClass.id)
        .where(Student.id == current_user["username"])
    )
    row = stu_result.one_or_none()
    if not row or not row[1]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到学生信息或未分配班级")
    cls = row[1]

    plan_result = await db.execute(
        select(TrainingPlan).where(TrainingPlan.major == cls.major, TrainingPlan.grade == cls.grade)
    )
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到匹配的培养方案")

    from app.models.score import Score, ScoreType
    from app.models.schedule import Schedule

    scores = await db.execute(
        select(Score, Schedule, Subject).join(Schedule, Score.schedule_id == Schedule.id)
        .join(Subject, Schedule.subject_id == Subject.id)
        .where(Score.student_id == current_user["username"], Score.score_type == ScoreType.total)
    )
    passed = {}
    for sc, sch, subj in scores:
        if sc.gpa and sc.gpa > 0:
            passed[subj.id] = float(sc.gpa)

    courses_result = await db.execute(
        select(PlanCourse, Subject).join(Subject, PlanCourse.subject_id == Subject.id)
        .where(PlanCourse.plan_id == plan.id)
    )
    courses = []
    for pc, subj in courses_result:
        status = "已通过" if subj.id in passed else "未修"
        courses.append({
            "id": pc.id, "subject_id": subj.id, "subject_name": subj.name,
            "course_type": pc.course_type, "credit": float(pc.credit),
            "limited_group": pc.limited_group, "min_required": pc.min_required,
            "status": status, "gpa": passed.get(subj.id)
        })

    total_earned = sum(float(subj.credit) for subj_id, gpa in passed.items()
                       for pc, subj in courses_result if subj.id == subj_id)
    elective_earned = sum(float(subj.credit) for subj_id, gpa in passed.items()
                          for pc, subj in courses_result if subj.id == subj_id and pc.course_type == "elective")

    return {
        "plan": {
            "id": plan.id, "major": plan.major, "grade": plan.grade,
            "total_credits_required": float(plan.total_credits_required),
            "elective_credits_required": float(plan.elective_credits_required),
            "total_credits_earned": total_earned,
            "elective_credits_earned": elective_earned,
        },
        "courses": courses,
    }
