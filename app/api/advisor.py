"""
辅导员/学院审批接口
GET  /advisor/pending-approvals  — 辅导员查看待审批请假
POST /advisor/approve            — 辅导员/学院审批请假
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models.teacher import Teacher
from app.models.student_class import StudentClass
from app.models.student import Student
from app.schemas.leave import (
    ApprovalRequest, LeaveItem, LeaveListResponse,
)
from app.services.leave_service import leave_service

router = APIRouter(prefix="/advisor", tags=["审批"])


@router.get("/pending-approvals", response_model=LeaveListResponse, summary="待审批请假")
async def pending_approvals(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = current_user["role"]
    if role not in ("teacher", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无审批权限")

    approver_role = "advisor"  # 默认辅导员
    class_id = None
    if role == "teacher":
        # 查找教师关联的班级（作为辅导员）
        teacher_job = current_user["username"]
        t_result = await db.execute(select(Teacher).where(Teacher.job_number == teacher_job))
        teacher = t_result.scalar_one_or_none()
        if not teacher:
            return LeaveListResponse(leaves=[])
        cls_result = await db.execute(
            select(StudentClass).where(StudentClass.advisor_id == teacher.id)
        )
        classes = cls_result.scalars().all()
        if not classes:
            return LeaveListResponse(leaves=[])
        class_id = classes[0].id

    rows = await leave_service.get_pending_approvals(db, approver_role, class_id)
    return LeaveListResponse(leaves=[
        LeaveItem(
            id=l.id, student_id=l.student_id, student_name=s.name,
            start_date=l.start_date.isoformat(), end_date=l.end_date.isoformat(),
            total_days=l.total_days, reason=l.reason, status=l.status,
            submit_time=l.submit_time.strftime("%Y-%m-%d %H:%M"),
        ) for l, s in rows
    ])


@router.post("/approve", summary="审批请假")
async def approve_leave(
    req: ApprovalRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = current_user["role"]
    if role not in ("teacher", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无审批权限")

    approver_role = "admin" if role == "admin" else "advisor"
    try:
        leave = await leave_service.approve(
            db, req.leave_id, current_user["username"],
            approver_role, req.result, req.comment,
        )
        return {"message": f"审批完成，状态：{leave.status}"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
