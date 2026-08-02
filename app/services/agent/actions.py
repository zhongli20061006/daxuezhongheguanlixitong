"""动作执行器：权限复核 → 数据拉取 → 上下文组装 → 写操作预检与确认执行。"""
import json
import logging
from datetime import date, datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Classroom, CourseCapacity, CourseSelection, Schedule, Student, Subject, SystemConfig, Teacher,
)
from app.services.agent.confirmations import ConfirmationStore
from app.services.agent.intent import Intent, IntentType
from app.services.agent.llm import OllamaClient
from app.services.agent.session import SessionStore

logger = logging.getLogger("student_management")

WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

STUDENT_ONLY = frozenset({IntentType.query_schedule, IntentType.study_plan, IntentType.enroll, IntentType.drop})
NOT_FOR_ADMIN = frozenset({IntentType.reserve_classroom, IntentType.repair_submit, IntentType.leave_apply})


def _allowed(intent: IntentType, role: str) -> bool:
    if intent in STUDENT_ONLY and role != "student":
        return False
    if intent in NOT_FOR_ADMIN and role == "admin":
        return False
    return True


def _period_range(period: str) -> tuple[int, int]:
    parts = period.split("-")
    return int(parts[0]), int(parts[-1])


def _periods_overlap(a: str, b: str) -> bool:
    a1, a2 = _period_range(a)
    b1, b2 = _period_range(b)
    return max(a1, b1) <= min(a2, b2)


def _weeks_overlap(a: str, b: str) -> bool:
    def rng(s: str) -> tuple[int, int]:
        s = s.strip()
        if "-" in s:
            x, y = s.split("-", 1)
            return int(x), int(y)
        return int(s), int(s)

    a1, a2 = rng(a)
    b1, b2 = rng(b)
    return max(a1, b1) <= min(a2, b2)


def _tomorrow_weekday() -> int:
    return (date.today() + timedelta(days=1)).isoweekday()


class ActionExecutor:
    def __init__(self, llm: OllamaClient, confirmations: ConfirmationStore, sessions: SessionStore):
        self.llm = llm
        self.confirmations = confirmations
        self.sessions = sessions

    async def execute(self, intent: Intent, user_id: str, role: str, session_id: str, db: AsyncSession, raw_text: str = "") -> list:
        from app.services.agent import AgentMessage

        if not _allowed(intent.intent, role):
            return [AgentMessage(kind="error", title="业务失败", content="无权限执行该操作")]
        if intent.intent == IntentType.chat:
            return await self._handle_chat(user_id, session_id, raw_text)
        handler = getattr(self, f"_handle_{intent.intent.value}", None)
        if handler is None:
            return await self._handle_navigate(
                Intent(intent=IntentType.navigate, params={"page": "/"}), user_id, role, session_id, db
            )
        return await handler(intent, user_id, role, session_id, db)

    async def _handle_navigate(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        page = intent.params.get("page") or "/"
        return [AgentMessage(kind="card", title="页面跳转", content=f"正在前往：{page}", navigation=page)]

    async def _handle_query_schedule(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        courses = await self._tomorrow_schedule(user_id, db)
        if not courses:
            return [AgentMessage(kind="card", title="明天的课表", content="明天没有课", data={"courses": []})]
        return [AgentMessage(kind="card", title="明天的课表", content=f"明天共 {len(courses)} 节课", data={"courses": courses})]

    async def _handle_study_plan(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        courses = await self._tomorrow_schedule(user_id, db)
        if not courses:
            return [AgentMessage(kind="card", title="学习方案", content="明天没有课，可以自主安排学习或休息", data={"courses": []})]
        plan_text = await self._generate_plan(courses)
        return [AgentMessage(kind="card", title="明天的学习方案", content=plan_text, data={"courses": courses})]

    async def _handle_chat(self, user_id, session_id, raw_text):
        from app.services.agent import AgentMessage

        context = self.sessions.build_context(user_id, session_id)
        if not context or context[-1]["content"] != raw_text:
            context.append({"role": "user", "content": raw_text or "你好"})
        reply = await self.llm.chat(context)
        return [AgentMessage(kind="text", content=reply)]

    async def _handle_enroll(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        schedule_id = await self._resolve_schedule_id(intent.params.get("course", ""), user_id, db)
        if schedule_id is None:
            return [AgentMessage(kind="error", title="业务失败", content="没找到要选的课程，请说完整的课程名")]
        ok, reason, info = await self._precheck_enroll(user_id, schedule_id, db)
        if not ok:
            return [AgentMessage(kind="error", title="业务失败", content=reason, data=info)]
        token = self.confirmations.create(user_id, {
            "action": "enroll", "schedule_id": schedule_id, "user_id": user_id, "session_id": session_id,
        })
        return [AgentMessage(kind="confirmation", title="确认选课", content=reason, data=info, confirm_token=token)]

    async def _handle_drop(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        schedule_id = await self._resolve_schedule_id(intent.params.get("course", ""), user_id, db)
        if schedule_id is None:
            return [AgentMessage(kind="error", title="业务失败", content="没找到要退的课程")]
        row = (await db.execute(
            select(CourseSelection, Schedule, Subject)
            .join(Schedule, CourseSelection.schedule_id == Schedule.id)
            .join(Subject, Schedule.subject_id == Subject.id)
            .where(
                CourseSelection.student_id == user_id,
                CourseSelection.schedule_id == schedule_id,
                CourseSelection.status == 1,
            )
        )).one_or_none()
        if not row:
            return [AgentMessage(kind="error", title="业务失败", content="未选该课程，无法退课")]
        token = self.confirmations.create(user_id, {
            "action": "drop", "schedule_id": schedule_id, "user_id": user_id, "session_id": session_id,
        })
        return [AgentMessage(
            kind="confirmation", title="确认退课", content=f"确认退掉课程：{row[2].name}",
            data={"course": row[2].name}, confirm_token=token,
        )]

    async def _handle_query_classroom(self, intent, user_id, role, session_id, db):
        return await self._handle_navigate(
            Intent(intent=IntentType.navigate, params={"page": "/classrooms"}), user_id, role, session_id, db
        )

    async def _handle_reserve_classroom(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        return [AgentMessage(
            kind="card", title="教室预约", content="教室预约功能下一期接入，先为你打开教室页面", navigation="/classrooms",
        )]

    async def _handle_repair_submit(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        return [AgentMessage(
            kind="card", title="报修", content="报修功能下一期接入，先为你打开报修页面", navigation="/repairs",
        )]

    async def _handle_leave_apply(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        return [AgentMessage(
            kind="card", title="请假", content="请假功能下一期接入，先为你打开请假页面", navigation="/leaves",
        )]

    async def execute_confirm(self, payload: dict, db: AsyncSession) -> list:
        from app.services.agent import AgentMessage

        if not payload:
            return [AgentMessage(kind="error", content="确认已过期或不存在，请重新发起")]
        action = payload.get("action")
        user_id = payload["user_id"]
        session_id = payload.get("session_id", "")
        if action == "enroll":
            schedule_id = int(payload["schedule_id"])
            ok, reason, info = await self._precheck_enroll(user_id, schedule_id, db)
            if not ok:
                return [AgentMessage(kind="error", title="业务失败", content=reason, data=info)]
            try:
                cap = await db.execute(text(
                    "UPDATE course_capacity SET enrolled = enrolled + 1 "
                    "WHERE schedule_id = :sid AND enrolled < capacity"
                ), {"sid": schedule_id})
                if cap.rowcount == 0:
                    await db.rollback()
                    return [AgentMessage(kind="error", title="业务失败", content="课程已满")]
                db.add(CourseSelection(student_id=user_id, schedule_id=schedule_id, status=1))
                await db.commit()
            except Exception:
                await db.rollback()
                logger.exception("agent enroll failed")
                return [AgentMessage(kind="error", title="系统异常", content="选课失败，请稍后重试")]
            self.sessions.add_fact(user_id, session_id, f"已选课：{info.get('course', schedule_id)}")
            return [AgentMessage(kind="card", title="选课成功", content=f"已成功选课：{info.get('course')}", data=info)]
        if action == "drop":
            schedule_id = int(payload["schedule_id"])
            try:
                upd = await db.execute(text(
                    "UPDATE course_selection SET status = 0, cancel_time = :now "
                    "WHERE student_id = :sid AND schedule_id = :schid AND status = 1"
                ), {"sid": user_id, "schid": schedule_id, "now": datetime.now()})
                if upd.rowcount == 0:
                    await db.rollback()
                    return [AgentMessage(kind="error", title="业务失败", content="该课程已退选")]
                await db.execute(text(
                    "UPDATE course_capacity SET enrolled = enrolled - 1 "
                    "WHERE schedule_id = :schid AND enrolled > 0"
                ), {"schid": schedule_id})
                await db.commit()
            except Exception:
                await db.rollback()
                logger.exception("agent drop failed")
                return [AgentMessage(kind="error", title="系统异常", content="退课失败，请稍后重试")]
            self.sessions.add_fact(user_id, session_id, f"已退课：{schedule_id}")
            return [AgentMessage(kind="card", title="退课成功", content="退课成功")]
        return [AgentMessage(kind="error", content="未知的确认动作")]

    async def _resolve_schedule_id(self, course: str, student_id: str, db) -> int | None:
        if course.isdigit():
            return int(course)
        stu = (await db.execute(select(Student).where(Student.id == student_id))).scalar_one_or_none()
        if not stu or not stu.class_id:
            return None
        rows = (await db.execute(
            select(Schedule.id, Subject.name)
            .join(Subject, Schedule.subject_id == Subject.id)
            .where(Schedule.class_id == stu.class_id)
        )).all()
        for sid, name in rows:
            if course in name:
                return sid
        return None

    async def _selection_window(self, db) -> tuple[bool, str]:
        configs = {
            c.config_key: c.config_value
            for c in (await db.execute(
                select(SystemConfig).where(SystemConfig.config_key.in_(["selection_start_time", "selection_end_time"]))
            )).scalars().all()
        }
        start_str = configs.get("selection_start_time")
        end_str = configs.get("selection_end_time")
        if not start_str or not end_str:
            return True, ""
        try:
            start = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return False, "选课时间配置错误"
        now = datetime.now()
        if now < start:
            return False, "选课尚未开放"
        if now > end:
            return False, "选课已结束"
        return True, ""

    async def _precheck_enroll(self, student_id: str, schedule_id: int, db) -> tuple[bool, str, dict]:
        row = (await db.execute(
            select(Schedule, Subject, Teacher, Classroom)
            .join(Subject, Schedule.subject_id == Subject.id)
            .join(Teacher, Schedule.teacher_id == Teacher.id)
            .join(Classroom, Schedule.classroom_id == Classroom.id)
            .where(Schedule.id == schedule_id)
        )).one_or_none()
        if not row:
            return False, "课表记录不存在", {}
        schedule, subject, teacher, classroom = row
        if subject.type.value == "compulsory":
            return False, "必修课无需选课", {}
        window_ok, window_msg = await self._selection_window(db)
        if not window_ok:
            return False, window_msg, {}
        dup = (await db.execute(select(CourseSelection).where(
            CourseSelection.student_id == student_id,
            CourseSelection.schedule_id == schedule_id,
            CourseSelection.status == 1,
        ))).scalar_one_or_none()
        if dup:
            return False, "该课程已选，请勿重复", {}
        cap = (await db.execute(select(CourseCapacity).where(CourseCapacity.schedule_id == schedule_id))).scalar_one_or_none()
        if not cap or cap.enrolled >= cap.capacity:
            return False, "课程已满", {}
        if await self._has_conflict(student_id, schedule, db):
            return False, "与已有课表时间冲突", {}
        info = {
            "course": subject.name, "teacher": teacher.name, "classroom": classroom.name,
            "day": WEEKDAY_CN[schedule.day_of_week - 1], "period": schedule.period,
            "weeks": schedule.weeks, "credit": float(subject.credit),
            "enrolled": cap.enrolled, "capacity": cap.capacity,
        }
        return True, "预检通过，确认后执行选课", info

    async def _has_conflict(self, student_id: str, target: Schedule, db) -> bool:
        stu = (await db.execute(select(Student).where(Student.id == student_id))).scalar_one_or_none()
        rows = []
        if stu and stu.class_id:
            rows.extend((await db.execute(
                select(Schedule).where(Schedule.class_id == stu.class_id, Schedule.semester == target.semester)
            )).scalars().all())
        rows.extend((await db.execute(
            select(Schedule).join(CourseSelection, CourseSelection.schedule_id == Schedule.id)
            .where(CourseSelection.student_id == student_id, CourseSelection.status == 1)
        )).scalars().all())
        seen: set[int] = set()
        for s in rows:
            if s.id == target.id or s.id in seen:
                continue
            seen.add(s.id)
            if s.day_of_week == target.day_of_week and _periods_overlap(s.period, target.period) and _weeks_overlap(s.weeks, target.weeks):
                return True
        return False

    async def _tomorrow_schedule(self, student_id: str, db) -> list[dict]:
        target = _tomorrow_weekday()
        stu = (await db.execute(select(Student).where(Student.id == student_id))).scalar_one_or_none()
        if not stu or not stu.class_id:
            return []
        courses: list[dict] = []
        for s, subj, t, cr in (await db.execute(
            select(Schedule, Subject, Teacher, Classroom)
            .join(Subject, Schedule.subject_id == Subject.id)
            .join(Teacher, Schedule.teacher_id == Teacher.id)
            .join(Classroom, Schedule.classroom_id == Classroom.id)
            .where(Schedule.class_id == stu.class_id, Schedule.day_of_week == target)
        )).all():
            courses.append(self._course_dict(s, subj, t, cr))
        seen = {c["schedule_id"] for c in courses}
        for s, subj, t, cr in (await db.execute(
            select(Schedule, Subject, Teacher, Classroom)
            .join(CourseSelection, CourseSelection.schedule_id == Schedule.id)
            .join(Subject, Schedule.subject_id == Subject.id)
            .join(Teacher, Schedule.teacher_id == Teacher.id)
            .join(Classroom, Schedule.classroom_id == Classroom.id)
            .where(CourseSelection.student_id == student_id, CourseSelection.status == 1, Schedule.day_of_week == target)
        )).all():
            if s.id not in seen:
                courses.append(self._course_dict(s, subj, t, cr))
        courses.sort(key=lambda c: c["period"])
        return courses

    @staticmethod
    def _course_dict(s, subj, t, cr) -> dict:
        return {
            "schedule_id": s.id, "course": subj.name, "teacher": t.name,
            "classroom": cr.name, "day": WEEKDAY_CN[s.day_of_week - 1],
            "period": s.period, "weeks": s.weeks, "credit": float(subj.credit),
        }

    async def _generate_plan(self, courses: list[dict]) -> str:
        schedule_lines = "\n".join(
            f"- {c['course']}（{c['day']} {c['period']}节，{c['classroom']}，{c['teacher']}）" for c in courses
        )
        prompt = (
            "你是大学生学习规划助手。根据明天的课表生成学习方案，输出 JSON："
            '{"courses":[{"course":"课程名","duration_minutes":60,"preview":"预习要点","review":"复习要点","priority":"高/中/低"}],"summary":"一句话整体安排"}'
            f"\n明天的课表：\n{schedule_lines}"
        )
        try:
            data = await self.llm.extract_json([
                {"role": "system", "content": "只输出 JSON，不要多余文字。"},
                {"role": "user", "content": prompt},
            ])
            return json.dumps(data, ensure_ascii=False)
        except Exception as exc:  # 模型不可用时降级模板
            logger.warning("study plan fell back to template: %s", exc)
            return self._template_plan(courses)

    @staticmethod
    def _template_plan(courses: list[dict]) -> str:
        lines = [f"明天共 {len(courses)} 节课，建议学习方案："]
        for c in courses:
            lines.append(f"- {c['course']}（{c['period']}节）：课前预习 20 分钟，课后复习 40 分钟，整理课堂笔记。")
        lines.append("整体安排：优先完成作业与复习，睡前快速回顾明天的课程要点。")
        return "\n".join(lines)
