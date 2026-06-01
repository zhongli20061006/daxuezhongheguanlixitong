"""
内部服务接口（供前端或定时任务调用）
GET /internal/summary — 系统概览数据
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_role
from app.models import Student, Teacher, Staff, Repair

router = APIRouter(prefix="/internal", tags=["内部"])


@router.get("/summary", summary="系统概览")
async def system_summary(
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    stu_count = await db.execute(select(func.count(Student.id)))
    teacher_count = await db.execute(select(func.count(Teacher.id)))
    staff_count = await db.execute(select(func.count(Staff.id)))
    pending_repair = await db.execute(
        select(func.count(Repair.id)).where(
            Repair.status.in_(["提交", "已接单", "处理中"])
        )
    )
    return {
        "student_count": stu_count.scalar(),
        "teacher_count": teacher_count.scalar(),
        "staff_count": staff_count.scalar(),
        "pending_repair_count": pending_repair.scalar(),
    }
