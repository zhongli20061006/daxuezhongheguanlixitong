"""
请假接口
POST /leave/apply        — 学生提交请假申请
GET  /leave/my           — 学生查看自己的请假
POST /leave/{id}/cancel  — 学生撤销请假
GET  /leave/{id}/detail  — 查看请假详情+审批记录
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models.leave_application import LeaveApplication
from app.models.student import Student
from app.schemas.leave import (
    LeaveApplyRequest, LeaveItem, LeaveListResponse,
    ApprovalRecordItem, LeaveDetailResponse,
)
from app.services.leave_service import leave_service

router = APIRouter(prefix="/leave", tags=["请假"])


@router.post("/apply", summary="提交请假申请")
async def apply_leave(
    req: LeaveApplyRequest,
    current_user: dict = Depends(require_role("student")),
    db: AsyncSession = Depends(get_db),
):
    try:
        leave = await leave_service.apply(
            db, current_user["username"], req.start_date, req.end_date, req.reason
        )
        return {"message": "请假申请已提交", "id": leave.id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/my", response_model=LeaveListResponse, summary="我的请假")
async def my_leaves(
    current_user: dict = Depends(require_role("student")),
    db: AsyncSession = Depends(get_db),
):
    leaves = await leave_service.get_my_leaves(db, current_user["username"])
    return LeaveListResponse(leaves=[
        LeaveItem(
            id=l.id, student_id=l.student_id,
            start_date=l.start_date.isoformat(), end_date=l.end_date.isoformat(),
            total_days=l.total_days, reason=l.reason, status=l.status,
            submit_time=l.submit_time.strftime("%Y-%m-%d %H:%M"),
        ) for l in leaves
    ])


@router.post("/{leave_id}/cancel", summary="撤销请假")
async def cancel_leave(
    leave_id: int,
    current_user: dict = Depends(require_role("student")),
    db: AsyncSession = Depends(get_db),
):
    try:
        await leave_service.cancel(db, leave_id, current_user["username"])
        return {"message": "请假已撤销"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{leave_id}/detail", response_model=LeaveDetailResponse, summary="请假详情")
async def leave_detail(
    leave_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LeaveApplication, Student)
        .join(Student, LeaveApplication.student_id == Student.id)
        .where(LeaveApplication.id == leave_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="请假申请不存在")
    l, stu = row
    records = await leave_service.get_approval_history(db, leave_id)
    return LeaveDetailResponse(
        leave=LeaveItem(
            id=l.id, student_id=l.student_id, student_name=stu.name,
            start_date=l.start_date.isoformat(), end_date=l.end_date.isoformat(),
            total_days=l.total_days, reason=l.reason, status=l.status,
            submit_time=l.submit_time.strftime("%Y-%m-%d %H:%M"),
        ),
        approvals=[
            ApprovalRecordItem(
                id=r.id, leave_id=r.leave_id, approver_id=r.approver_id,
                approver_role=r.approver_role, level=r.level,
                result=r.result, comment=r.comment,
                created_at=r.created_at.strftime("%Y-%m-%d %H:%M"),
            ) for r in records
        ]
    )
