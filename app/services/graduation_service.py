"""
毕业审核服务
根据培养方案审核学生是否满足毕业条件
"""
import json
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.graduation_audit import GraduationAudit
from app.models.training_plan import TrainingPlan
from app.models.plan_course import PlanCourse
from app.models.score import Score, ScoreType
from app.models.course_selection import CourseSelection
from app.models.schedule import Schedule
from app.models.subject import Subject
from app.models.student import Student


class GraduationService:

    async def audit_student(
        self, db: AsyncSession, student_id: str, plan_id: int | None = None
    ) -> GraduationAudit:
        # 获取学生信息
        stu_result = await db.execute(select(Student).where(Student.id == student_id))
        student = stu_result.scalar_one_or_none()
        if not student or not student.class_id:
            raise ValueError("学生不存在或未分配班级")

        # 获取培养方案
        if plan_id:
            plan_result = await db.execute(
                select(TrainingPlan).where(TrainingPlan.id == plan_id)
            )
        else:
            # 从班级信息推断方案（major + grade）
            from app.models.student_class import StudentClass
            cls_result = await db.execute(
                select(StudentClass).where(StudentClass.id == student.class_id)
            )
            cls = cls_result.scalar_one_or_none()
            if not cls:
                raise ValueError("班级信息不存在")
            plan_result = await db.execute(
                select(TrainingPlan).where(
                    TrainingPlan.major == cls.major,
                    TrainingPlan.grade == cls.grade,
                )
            )
        plan = plan_result.scalar_one_or_none()
        if not plan:
            raise ValueError("未找到匹配的培养方案")

        # 获取方案中的所有课程
        pc_result = await db.execute(
            select(PlanCourse, Subject)
            .join(Subject, PlanCourse.subject_id == Subject.id)
            .where(PlanCourse.plan_id == plan.id)
        )
        plan_courses = pc_result.all()

        # 获取学生所有总评成绩（已通过 = GPA > 0 且不为0分）
        scores_result = await db.execute(
            select(Score, Schedule, Subject)
            .join(Schedule, Score.schedule_id == Schedule.id)
            .join(Subject, Schedule.subject_id == Subject.id)
            .where(
                Score.student_id == student_id,
                Score.score_type == ScoreType.total,
            )
        )
        passed_subjects = {}  # subject_id -> gpa
        total_credits_earned = 0.0
        elective_credits_earned = 0.0
        for sc, sch, subj in scores_result:
            if sc.gpa and sc.gpa > 0:
                passed_subjects[subj.id] = sc.gpa
                credit = float(subj.credit)
                total_credits_earned += credit
                if subj.type.value == "elective":
                    elective_credits_earned += credit

        # 审核必修课
        compulsory_total = 0
        compulsory_passed = 0
        for pc, subj in plan_courses:
            if pc.course_type == "compulsory":
                compulsory_total += 1
                if subj.id in passed_subjects:
                    compulsory_passed += 1

        # 审核限选各组
        limited_groups: dict[str, dict] = {}  # group_name -> {passed, required}
        for pc, subj in plan_courses:
            if pc.course_type == "limited" and pc.limited_group:
                group_name = pc.limited_group
                if group_name not in limited_groups:
                    limited_groups[group_name] = {"passed": 0, "required": pc.min_required or 0}
                if subj.id in passed_subjects:
                    limited_groups[group_name]["passed"] += 1

        limited_all_ok = all(
            g["passed"] >= g["required"] for g in limited_groups.values()
        )

        # 判断是否可毕业
        is_graduatable = (
            compulsory_passed >= compulsory_total
            and limited_all_ok
            and total_credits_earned >= float(plan.total_credits_required)
            and elective_credits_earned >= float(plan.elective_credits_required)
        )

        detail_parts = []
        if compulsory_passed < compulsory_total:
            detail_parts.append(f"必修课：{compulsory_passed}/{compulsory_total}未通过")
        for name, g in limited_groups.items():
            if g["passed"] < g["required"]:
                detail_parts.append(f"限选组{name}：{g['passed']}/{g['required']}")
        if total_credits_earned < float(plan.total_credits_required):
            detail_parts.append(f"总学分不足：{total_credits_earned}/{float(plan.total_credits_required)}")
        if elective_credits_earned < float(plan.elective_credits_required):
            detail_parts.append(f"选修学分不足：{elective_credits_earned}/{float(plan.elective_credits_required)}")

        detail = "；".join(detail_parts) if detail_parts else "满足所有毕业条件"

        # UPSERT 审核结果
        audit_result = await db.execute(
            select(GraduationAudit).where(
                GraduationAudit.student_id == student_id,
                GraduationAudit.plan_id == plan.id,
            )
        )
        audit = audit_result.scalar_one_or_none()
        if not audit:
            audit = GraduationAudit(student_id=student_id, plan_id=plan.id)
            db.add(audit)

        audit.total_credits_earned = total_credits_earned
        audit.elective_credits_earned = elective_credits_earned
        audit.compulsory_passed = compulsory_passed
        audit.compulsory_total = compulsory_total
        audit.limited_groups_passed = json.dumps(
            {k: v["passed"] for k, v in limited_groups.items()}, ensure_ascii=False
        )
        audit.is_graduatable = is_graduatable
        audit.detail = detail

        await db.commit()
        await db.refresh(audit)
        return audit

    async def get_audit_list(self, db: AsyncSession, major: str | None = None, grade: int | None = None):
        stmt = select(GraduationAudit, Student, TrainingPlan).join(
            Student, GraduationAudit.student_id == Student.id
        ).join(
            TrainingPlan, GraduationAudit.plan_id == TrainingPlan.id
        )
        if major:
            stmt = stmt.where(TrainingPlan.major == major)
        if grade:
            stmt = stmt.where(TrainingPlan.grade == grade)
        stmt = stmt.order_by(GraduationAudit.student_id)
        result = await db.execute(stmt)
        return result.all()


graduation_service = GraduationService()
