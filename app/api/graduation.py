"""
毕业审核接口
POST /graduation/audit/{student_id}  — 审核单个学生
POST /graduation/audit-batch          — 批量审核
GET  /graduation/audits               — 审核结果列表（分页）
GET  /graduation/my                   — 我的审核结果（单对象）
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.deps import require_role, get_current_user
from app.models.training_plan import TrainingPlan
from app.models.student import Student
from app.models.student_class import StudentClass
from app.schemas.training import AuditItem, AuditListResponse
from app.services.graduation_service import graduation_service

router = APIRouter(prefix="/graduation", tags=["毕业审核"])


@router.post("/audit/{student_id}", summary="审核单个学生")
async def audit_student(
    student_id: str,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        audit = await graduation_service.audit_student(db, student_id)
        return {"message": "审核完成", "is_graduatable": audit.is_graduatable, "detail": audit.detail}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/audit-batch", summary="批量审核")
async def audit_batch(
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    major: str | None = Query(None, description="专业筛选"),
    grade: int | None = Query(None, description="年级筛选"),
):
    stmt = select(Student).join(StudentClass, Student.class_id == StudentClass.id)
    if major:
        stmt = stmt.where(StudentClass.major == major)
    if grade:
        stmt = stmt.where(StudentClass.grade == grade)
    result = await db.execute(stmt)
    students = result.scalars().all()

    student_ids = [s.id for s in students]
    results = await graduation_service.audit_batch_students(db, student_ids)

    return {
        "total": len(results),
        "results": [
            {"student_id": a.student_id, "is_graduatable": a.is_graduatable, "detail": a.detail}
            for a in results
        ]
    }


@router.get("/audits", response_model=AuditListResponse, summary="审核结果列表")
async def list_audits(
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
    major: str | None = None,
    grade: int | None = None,
    limit: int = Query(50, ge=1, le=200, description="每页条数"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    rows = await graduation_service.get_audit_list(db, major, grade, limit, offset)
    return AuditListResponse(audits=[
        AuditItem(
            id=a.id, student_id=a.student_id, student_name=s.name,
            plan_id=a.plan_id, major=p.major,
            total_credits_earned=float(a.total_credits_earned),
            total_credits_required=float(p.total_credits_required),
            elective_credits_earned=float(a.elective_credits_earned),
            elective_credits_required=float(p.elective_credits_required),
            compulsory_passed=a.compulsory_passed,
            compulsory_total=a.compulsory_total,
            limited_groups_passed=a.limited_groups_passed,
            is_graduatable=a.is_graduatable,
            detail=a.detail,
            updated_at=a.updated_at.strftime("%Y-%m-%d %H:%M"),
        ) for a, s, p in rows
    ])


@router.get("/my", summary="我的毕业审核结果")
async def my_audit(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.graduation_audit import GraduationAudit

    result = await db.execute(
        select(GraduationAudit, TrainingPlan, StudentClass)
        .join(TrainingPlan, GraduationAudit.plan_id == TrainingPlan.id)
        .join(Student, GraduationAudit.student_id == Student.id)
        .join(StudentClass, Student.class_id == StudentClass.id)
        .where(GraduationAudit.student_id == current_user["username"])
        .order_by(GraduationAudit.updated_at.desc())
        .limit(1)
    )
    rows = result.all()
    if not rows:
        return {"audit": None}
    a, p, c = rows[0]
    return {"audit": {
        "id": a.id, "student_id": a.student_id,
        "major": p.major, "grade": p.grade,
        "total_credits_earned": float(a.total_credits_earned),
        "total_credits_required": float(p.total_credits_required),
        "elective_credits_earned": float(a.elective_credits_earned),
        "elective_credits_required": float(p.elective_credits_required),
        "compulsory_passed": a.compulsory_passed,
        "compulsory_total": a.compulsory_total,
        "limited_groups_passed": a.limited_groups_passed,
        "is_graduatable": a.is_graduatable,
        "detail": a.detail,
        "updated_at": a.updated_at.strftime("%Y-%m-%d %H:%M"),
    }}
