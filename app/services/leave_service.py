"""
请假服务
处理请假申请的业务逻辑：冲突检测、多级审批流转
"""
import logging
from datetime import datetime, date
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leave_application import LeaveApplication, LeaveStatus
from app.models.approval_record import ApprovalRecord
from app.models.approval_config import ApprovalConfig
from app.models.student_class import StudentClass
from app.models.student import Student
from app.services.event_bus import Events, event_bus
from app.services.notification_service import notification_service as ns

logger = logging.getLogger("student_management")


class LeaveService:

    async def apply(
        self,
        db: AsyncSession,
        student_id: str,
        start_date_str: str,
        end_date_str: str,
        reason: str,
    ) -> LeaveApplication:
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
        if end_date < start_date:
            raise ValueError("结束日期不能早于开始日期")
        if start_date < date.today():
            raise ValueError("请假开始日期不能早于今天")

        total_days = (end_date - start_date).days + 1

        # 确定审批流程
        result = await db.execute(select(ApprovalConfig))
        configs = result.scalars().all()
        required_levels_str = "1"  # 默认辅导员审批
        for cfg in configs:
            if total_days >= cfg.min_days and (cfg.max_days is None or total_days <= cfg.max_days):
                required_levels_str = cfg.required_levels
                break

        levels = [int(lv.strip()) for lv in required_levels_str.split(",")]
        initial_status = LeaveStatus.PENDING_COUNSELOR.value if 1 in levels else LeaveStatus.PENDING_COLLEGE.value

        leave = LeaveApplication(
            student_id=student_id,
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            reason=reason,
            status=initial_status,
        )
        db.add(leave)
        await db.commit()
        await db.refresh(leave)

        # 获取学生姓名用于通知
        stu_result = await db.execute(select(Student).where(Student.id == student_id))
        student = stu_result.scalar_one_or_none()
        student_name = student.name if student else student_id

        # 创建通知（直接调用，保证可靠性）
        try:
            await ns.create_notification(
                db=db,
                title="新请假申请",
                content=f"学生 {student_name} 提交了 {leave.total_days} 天请假申请",
                recipient_role="teacher",
                event_type=Events.LEAVE_SUBMITTED,
            )
            await db.commit()
        except Exception:
            logger.warning("Failed to create notification for leave #%s", leave.id, exc_info=True)

        return leave

    async def approve(
        self,
        db: AsyncSession,
        leave_id: int,
        approver_id: str,
        approver_role: str,
        result: str,
        comment: str | None = None,
        is_college_admin: bool = False,
    ) -> LeaveApplication:
        leave_result = await db.execute(
            select(LeaveApplication).where(LeaveApplication.id == leave_id)
        )
        leave = leave_result.scalar_one_or_none()
        if not leave:
            raise ValueError("请假申请不存在")
        if leave.status in (LeaveStatus.APPROVED.value, LeaveStatus.REJECTED.value, LeaveStatus.CANCELLED.value):
            raise ValueError(f"该申请已{leave.status}，不能重复审批")

        # 确定当前审批级别
        if leave.status == LeaveStatus.PENDING_COUNSELOR.value:
            level = 1
            if approver_role not in ("advisor", "admin"):
                raise ValueError("当前审批阶段需要辅导员审批")
        elif leave.status == LeaveStatus.PENDING_COLLEGE.value:
            level = 2
            if not (is_college_admin or approver_role == "admin"):
                raise ValueError("当前审批阶段需要学院管理员审批")
        else:
            level = 1

        record = ApprovalRecord(
            leave_id=leave_id,
            approver_id=approver_id,
            approver_role=approver_role,
            level=level,
            result=result,
            comment=comment,
        )
        try:
            db.add(record)
            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise ValueError(f"该级别的审批已被处理，不能重复审批")

        if result == "驳回":
            leave.status = LeaveStatus.REJECTED.value
        elif result == "通过":
            if level == 1:
                required_levels = self._get_required_levels_for_days(leave.total_days)
                if 2 in required_levels:
                    leave.status = LeaveStatus.PENDING_COLLEGE.value
                else:
                    leave.status = LeaveStatus.APPROVED.value
            elif level == 2:
                leave.status = LeaveStatus.APPROVED.value

        await db.commit()
        await db.refresh(leave)

        if result == "通过" and leave.status == "已通过":
            try:
                await ns.create_notification(
                    db=db,
                    title="请假已通过",
                    content=f"请假申请（{leave.total_days}天）已通过审批",
                    recipient_id=leave.student_id,
                    event_type=Events.LEAVE_APPROVED,
                )
                await db.commit()
            except Exception:
                logger.warning("Failed to create approval notification for leave #%s", leave.id, exc_info=True)
        elif result == "驳回":
            try:
                await ns.create_notification(
                    db=db,
                    title="请假已驳回",
                    content=f"请假申请（{leave.total_days}天）已被驳回",
                    recipient_id=leave.student_id,
                    event_type=Events.LEAVE_REJECTED,
                )
                await db.commit()
            except Exception:
                logger.warning("Failed to create rejection notification for leave #%s", leave.id, exc_info=True)

        return leave

    async def cancel(self, db: AsyncSession, leave_id: int, student_id: str) -> LeaveApplication:
        leave_result = await db.execute(
            select(LeaveApplication).where(
                LeaveApplication.id == leave_id,
                LeaveApplication.student_id == student_id,
            )
        )
        leave = leave_result.scalar_one_or_none()
        if not leave:
            raise ValueError("请假申请不存在")
        if leave.status in (LeaveStatus.APPROVED.value, LeaveStatus.REJECTED.value, LeaveStatus.CANCELLED.value):
            raise ValueError("当前状态不可撤销")
        leave.status = LeaveStatus.CANCELLED.value
        leave.updated_at = datetime.now()
        await db.commit()
        return leave

    async def get_my_leaves(self, db: AsyncSession, student_id: str):
        result = await db.execute(
            select(LeaveApplication)
            .where(LeaveApplication.student_id == student_id)
            .order_by(LeaveApplication.submit_time.desc())
        )
        return result.scalars().all()

    async def get_pending_approvals(
        self, db: AsyncSession, approver_role: str, class_id: int | None = None
    ):
        if approver_role == "advisor":
            stmt = (
                select(LeaveApplication, Student)
                .join(Student, LeaveApplication.student_id == Student.id)
                .where(LeaveApplication.status == LeaveStatus.PENDING_COUNSELOR.value)
            )
            if class_id:
                stmt = stmt.where(Student.class_id == class_id)
            stmt = stmt.order_by(LeaveApplication.submit_time.asc())
        elif approver_role == "college":
            stmt = (
                select(LeaveApplication, Student)
                .join(Student, LeaveApplication.student_id == Student.id)
                .where(LeaveApplication.status == LeaveStatus.PENDING_COLLEGE.value)
                .order_by(LeaveApplication.submit_time.asc())
            )
        else:
            stmt = (
                select(LeaveApplication, Student)
                .join(Student, LeaveApplication.student_id == Student.id)
                .where(
                    LeaveApplication.status.in_([
                        LeaveStatus.PENDING_COUNSELOR.value,
                        LeaveStatus.PENDING_COLLEGE.value,
                    ])
                )
                .order_by(LeaveApplication.submit_time.asc())
            )
        result = await db.execute(stmt)
        return result.all()

    async def get_approval_history(self, db: AsyncSession, leave_id: int):
        result = await db.execute(
            select(ApprovalRecord)
            .where(ApprovalRecord.leave_id == leave_id)
            .order_by(ApprovalRecord.created_at.asc())
        )
        return result.scalars().all()

    def _get_required_levels_for_days(self, total_days: int) -> set[int]:
        return {1} if total_days < 3 else {1, 2}


leave_service = LeaveService()
