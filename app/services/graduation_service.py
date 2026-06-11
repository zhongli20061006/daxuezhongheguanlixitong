"""
毕业审核服务
根据培养方案审核学生是否满足毕业条件
"""
import json
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.graduation_audit import GraduationAudit
from app.models.training_plan import TrainingPlan
from app.models.plan_course import PlanCourse
from app.models.score import Score, ScoreType
from app.models.schedule import Schedule
from app.models.subject import Subject
from app.models.student import Student
from app.models.student_class import StudentClass


class GraduationService:

    async def audit_student(
        self, db: AsyncSession, student_id: str, plan_id: int | None = None
    ) -> GraduationAudit:
        stu_result = await db.execute(select(Student).where(Student.id == student_id))
        student = stu_result.scalar_one_or_none()
        if not student or not student.class_id:
            raise ValueError("学生不存在或未分配班级")

        if plan_id:
            plan_result = await db.execute(select(TrainingPlan).where(TrainingPlan.id == plan_id))
        else:
            from app.models.student_class import StudentClass
            cls_result = await db.execute(
                select(StudentClass).where(StudentClass.id == student.class_id)
            )
            cls = cls_result.scalar_one_or_none()
            if not cls:
                raise ValueError("班级信息不存在")
            plan_result = await db.execute(
                select(TrainingPlan).where(
                    TrainingPlan.major == cls.major, TrainingPlan.grade == cls.grade,
                )
            )
        plan = plan_result.scalar_one_or_none()
        if not plan:
            raise ValueError("未找到匹配的培养方案")

        pc_result = await db.execute(
            select(PlanCourse, Subject)
            .join(Subject, PlanCourse.subject_id == Subject.id)
            .where(PlanCourse.plan_id == plan.id)
        )
        plan_courses = pc_result.all()

        # 修复3: 重修取最高绩点 MAX(gpa)
        scores_result = await db.execute(
            select(
                func.max(Score.gpa).label("max_gpa"),
                Schedule.subject_id,
                func.min(Subject.credit).label("credit"),
            )
            .join(Schedule, Score.schedule_id == Schedule.id)
            .join(Subject, Schedule.subject_id == Subject.id)
            .where(
                Score.student_id == student_id,
                Score.score_type == ScoreType.total.value,
            )
            .group_by(Schedule.subject_id)
        )
        passed_subjects = {}  # subject_id -> (gpa, credit)
        total_credits_earned = 0.0
        for row in scores_result:
            if row.max_gpa and row.max_gpa > 0:
                credit = float(row.credit)
                passed_subjects[row.subject_id] = (float(row.max_gpa), credit)
                total_credits_earned += credit

        compulsory_total = 0
        compulsory_passed = 0
        elective_credits_earned = 0.0
        limited_groups: dict[str, dict] = {}

        for pc, subj in plan_courses:
            # 修复1: 按 plan_course.course_type 决定课程类别
            if pc.course_type == "compulsory":
                compulsory_total += 1
                if subj.id in passed_subjects:
                    compulsory_passed += 1
            elif pc.course_type == "elective":
                if subj.id in passed_subjects:
                    elective_credits_earned += passed_subjects[subj.id][1]
            elif pc.course_type == "limited" and pc.limited_group:
                group_name = pc.limited_group
                if group_name not in limited_groups:
                    limited_groups[group_name] = {"passed": 0, "required": pc.min_required or 0}
                if subj.id in passed_subjects:
                    limited_groups[group_name]["passed"] += 1

        limited_all_ok = all(
            g["passed"] >= g["required"] for g in limited_groups.values()
        )

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

    # 修复2: 批量审核优化 — 单次查询 + Python 聚合取代 N 次独立查询
    async def audit_batch_students(
        self, db: AsyncSession, student_ids: list[str]
    ) -> list[GraduationAudit]:
        if not student_ids:
            return []

        # 1. 一次性查询所有学生的班级和专业信息
        stu_result = await db.execute(
            select(Student, StudentClass)
            .join(StudentClass, Student.class_id == StudentClass.id)
            .where(Student.id.in_(student_ids))
        )
        student_rows = stu_result.all()

        # student_id -> (major, grade)
        student_class_info: dict[str, tuple[str, int]] = {}
        major_grade_pairs: set[tuple[str, int]] = set()
        for student, cls in student_rows:
            if cls.major and cls.grade:
                student_class_info[student.id] = (cls.major, cls.grade)
                major_grade_pairs.add((cls.major, cls.grade))

        if not major_grade_pairs:
            return []

        # 2. 一次性查询所有培养方案
        conditions = [
            and_(TrainingPlan.major == m, TrainingPlan.grade == g)
            for m, g in major_grade_pairs
        ]
        plan_result = await db.execute(
            select(TrainingPlan).where(or_(*conditions))
        )
        plans = plan_result.scalars().all()
        plan_by_key: dict[tuple[str, int], TrainingPlan] = {
            (p.major, p.grade): p for p in plans
        }

        # student_id -> plan_id
        student_plan: dict[str, int] = {}
        for sid in student_ids:
            info = student_class_info.get(sid)
            if info:
                plan = plan_by_key.get(info)
                if plan:
                    student_plan[sid] = plan.id

        if not student_plan:
            return []

        # 3. 一次性查询所有培养方案课程
        all_plan_ids = list(set(student_plan.values()))
        pc_result = await db.execute(
            select(PlanCourse, Subject)
            .join(Subject, PlanCourse.subject_id == Subject.id)
            .where(PlanCourse.plan_id.in_(all_plan_ids))
        )
        plan_courses_rows = pc_result.all()

        # plan_id -> [(PlanCourse, Subject), ...]
        plan_courses_by_plan: dict[int, list] = {}
        for pc, subj in plan_courses_rows:
            plan_courses_by_plan.setdefault(pc.plan_id, []).append((pc, subj))

        # 4. 一次性查询所有学生的成绩（MAX(gpa) per subject per student）
        scores_result = await db.execute(
            select(
                Score.student_id,
                Schedule.subject_id,
                func.max(Score.gpa).label("max_gpa"),
                func.min(Subject.credit).label("credit"),
            )
            .join(Schedule, Score.schedule_id == Schedule.id)
            .join(Subject, Schedule.subject_id == Subject.id)
            .where(
                Score.student_id.in_(student_ids),
                Score.score_type == ScoreType.total.value,
            )
            .group_by(Score.student_id, Schedule.subject_id)
        )
        score_rows = scores_result.all()

        # student_id -> {subject_id: (gpa, credit)}
        scores_by_student: dict[str, dict[int, tuple[float, float]]] = {}
        for row in score_rows:
            if row.max_gpa and row.max_gpa > 0:
                scores_by_student.setdefault(row.student_id, {})
                scores_by_student[row.student_id][row.subject_id] = (
                    float(row.max_gpa), float(row.credit)
                )

        total_credits_by_student: dict[str, float] = {}
        for sid, subjects in scores_by_student.items():
            total_credits_by_student[sid] = sum(c for _, c in subjects.values())

        # 5. 获取已有的审核记录
        existing = await db.execute(
            select(GraduationAudit).where(
                GraduationAudit.student_id.in_(student_ids)
            )
        )
        existing_audit_map: dict[tuple[str, int], GraduationAudit] = {}
        for a in existing.scalars().all():
            existing_audit_map[(a.student_id, a.plan_id)] = a

        # 6. Python 聚合 — 逐学生计算毕业状态
        results: list[GraduationAudit] = []
        for sid in student_ids:
            plan_id = student_plan.get(sid)
            if not plan_id:
                continue

            plan_courses = plan_courses_by_plan.get(plan_id, [])
            passed_subjects = scores_by_student.get(sid, {})

            compulsory_total = 0
            compulsory_passed = 0
            elective_credits_earned = 0.0
            limited_groups: dict[str, dict] = {}
            total_credits_earned = total_credits_by_student.get(sid, 0.0)

            for pc, subj in plan_courses:
                if pc.course_type == "compulsory":
                    compulsory_total += 1
                    if subj.id in passed_subjects:
                        compulsory_passed += 1
                elif pc.course_type == "elective":
                    if subj.id in passed_subjects:
                        elective_credits_earned += passed_subjects[subj.id][1]
                elif pc.course_type == "limited" and pc.limited_group:
                    group_name = pc.limited_group
                    if group_name not in limited_groups:
                        limited_groups[group_name] = {
                            "passed": 0, "required": pc.min_required or 0
                        }
                    if subj.id in passed_subjects:
                        limited_groups[group_name]["passed"] += 1

            limited_all_ok = all(
                g["passed"] >= g["required"] for g in limited_groups.values()
            )

            plan_obj = plan_by_key.get(student_class_info.get(sid, ()))
            plan_credits_total = float(plan_obj.total_credits_required) if plan_obj else 999999
            plan_elective_req = float(plan_obj.elective_credits_required) if plan_obj else 999999

            is_graduatable = (
                compulsory_passed >= compulsory_total
                and limited_all_ok
                and total_credits_earned >= plan_credits_total
                and elective_credits_earned >= plan_elective_req
            )

            detail_parts = []
            if compulsory_passed < compulsory_total:
                detail_parts.append(f"必修课：{compulsory_passed}/{compulsory_total}未通过")
            for name, g in limited_groups.items():
                if g["passed"] < g["required"]:
                    detail_parts.append(f"限选组{name}：{g['passed']}/{g['required']}")
            if plan_obj:
                if total_credits_earned < plan_credits_total:
                    detail_parts.append(
                        f"总学分不足：{total_credits_earned}/{plan_credits_total}"
                    )
                if elective_credits_earned < plan_elective_req:
                    detail_parts.append(
                        f"选修学分不足：{elective_credits_earned}/{plan_elective_req}"
                    )
            detail = "；".join(detail_parts) if detail_parts else "满足所有毕业条件"

            # 取或创建审核记录
            audit = existing_audit_map.get((sid, plan_id))
            if not audit:
                audit = GraduationAudit(student_id=sid, plan_id=plan_id)
                db.add(audit)

            audit.total_credits_earned = total_credits_earned
            audit.elective_credits_earned = elective_credits_earned
            audit.compulsory_passed = compulsory_passed
            audit.compulsory_total = compulsory_total
            audit.limited_groups_passed = json.dumps(
                {k: v["passed"] for k, v in limited_groups.items()},
                ensure_ascii=False,
            )
            audit.is_graduatable = is_graduatable
            audit.detail = detail

            results.append(audit)

        await db.commit()
        for audit in results:
            await db.refresh(audit)
        return results

    async def get_audit_list(
        self, db: AsyncSession,
        major: str | None = None, grade: int | None = None,
        limit: int = 50, offset: int = 0,  # 修复4: 分页
    ):
        stmt = (
            select(GraduationAudit, Student, TrainingPlan)
            .join(Student, GraduationAudit.student_id == Student.id)
            .join(TrainingPlan, GraduationAudit.plan_id == TrainingPlan.id)
        )
        if major:
            stmt = stmt.where(TrainingPlan.major == major)
        if grade:
            stmt = stmt.where(TrainingPlan.grade == grade)
        stmt = stmt.order_by(GraduationAudit.student_id).offset(offset).limit(limit)
        result = await db.execute(stmt)
        return result.all()


graduation_service = GraduationService()
