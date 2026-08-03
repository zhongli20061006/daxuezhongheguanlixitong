"""动作执行器：权限复核 → 数据拉取 → 上下文组装 → 写操作预检与确认执行。"""
import json
import logging
import re
from datetime import date, datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Classroom, ClassroomReservation, CourseCapacity, CourseSelection, Repair, RepairStatus,
    RepairType, Schedule, Student, Subject, SubjectType, SystemConfig, Teacher,
)
from app.services.agent.confirmations import ConfirmationStore
from app.services.agent.intent import Intent, IntentType, KNOWN_PAGES
from app.services.agent.llm import OllamaClient
from app.services.agent.session import SessionStore
from app.utils.period_parser import is_period_overlap
from app.utils.week_parser import is_week_matched

logger = logging.getLogger("student_management")

WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

STUDENT_ONLY = frozenset({
    IntentType.query_schedule, IntentType.study_plan, IntentType.enroll, IntentType.drop,
    IntentType.leave_apply,
})
NOT_FOR_ADMIN = frozenset({IntentType.reserve_classroom, IntentType.repair_submit, IntentType.leave_apply})

REPAIR_TYPES = frozenset(t.value for t in RepairType)

_RELATIVE_DAY = {"今天": 0, "明天": 1, "后天": 2, "大后天": 3}


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

        page = (intent.params.get("page") or "/").rstrip("/") or "/"
        if page not in KNOWN_PAGES:
            return [AgentMessage(kind="error", title="业务失败", content=f"无法识别目标页面：{page}")]
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

        schedule_id, hint = await self._resolve_schedule(intent.params.get("course", ""), user_id, db)
        if schedule_id is None:
            content = f"没找到要选的课程。{hint}" if hint else "没找到要选的课程，请说完整的课程名"
            return [AgentMessage(kind="error", title="业务失败", content=content)]
        ok, reason, info = await self._precheck_enroll(user_id, schedule_id, db)
        if not ok:
            return [AgentMessage(kind="error", title="业务失败", content=reason, data=info)]
        token = self.confirmations.create(user_id, {
            "action": "enroll", "schedule_id": schedule_id, "user_id": user_id, "session_id": session_id,
        })
        return [AgentMessage(kind="confirmation", title="确认选课", content=reason, data=info, confirm_token=token)]

    async def _handle_drop(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        schedule_id, hint = await self._resolve_schedule(intent.params.get("course", ""), user_id, db)
        if schedule_id is None:
            content = f"没找到要退的课程。{hint}" if hint else "没找到要退的课程"
            return [AgentMessage(kind="error", title="业务失败", content=content)]
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

        ok, reason, info = await self._precheck_reserve(intent.params, db)
        if not ok:
            self.sessions.set_pending_write(user_id, session_id, intent.intent.value, intent.params)
            return [AgentMessage(kind="error", title="业务失败", content=reason, data=info)]
        self.sessions.clear_pending_write(user_id, session_id)
        token = self.confirmations.create(user_id, {
            "action": "reserve_classroom", "classroom_id": info["classroom_id"],
            "week": info["week"], "day_of_week": info["day_of_week"], "period": info["period"],
            "reason": info["reason"], "role": role, "user_id": user_id, "session_id": session_id,
        })
        return [AgentMessage(
            kind="confirmation", title="确认预约教室",
            content=f"{info['classroom']}｜第{info['week']}周 {WEEKDAY_CN[info['day_of_week'] - 1]} {info['period']}节",
            data=info, confirm_token=token,
        )]

    async def _handle_repair_submit(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        ok, reason, info = self._precheck_repair(intent.params)
        if not ok:
            self.sessions.set_pending_write(user_id, session_id, intent.intent.value, intent.params)
            return [AgentMessage(kind="error", title="业务失败", content=reason, data=info)]
        self.sessions.clear_pending_write(user_id, session_id)
        token = self.confirmations.create(user_id, {
            "action": "repair_submit", "location": info["location"], "type": info["type"],
            "description": info["description"], "role": role, "user_id": user_id, "session_id": session_id,
        })
        return [AgentMessage(
            kind="confirmation", title="确认报修",
            content=f"{info['location']}｜{info['type']}：{info['description']}",
            data=info, confirm_token=token,
        )]

    async def _handle_leave_apply(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        ok, reason, info = self._precheck_leave(intent.params)
        if not ok:
            self.sessions.set_pending_write(user_id, session_id, intent.intent.value, intent.params)
            return [AgentMessage(kind="error", title="业务失败", content=reason, data=info)]
        self.sessions.clear_pending_write(user_id, session_id)
        token = self.confirmations.create(user_id, {
            "action": "leave_apply", "start_date": info["start_date"], "end_date": info["end_date"],
            "reason": info["reason"], "user_id": user_id, "session_id": session_id,
        })
        return [AgentMessage(
            kind="confirmation", title="确认请假",
            content=f"{info['start_date']} 至 {info['end_date']}，共 {info['total_days']} 天",
            data=info, confirm_token=token,
        )]

    async def execute_confirm(self, payload: dict, db: AsyncSession) -> list:
        from app.services.agent import AgentMessage

        if not payload:
            return [AgentMessage(kind="error", content="确认已过期或不存在，请重新发起")]
        action = payload.get("action")
        user_id = payload["user_id"]
        session_id = payload.get("session_id", "")
        self.sessions.clear_pending_write(user_id, session_id)
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
        if action == "leave_apply":
            ok, reason, info = self._precheck_leave(payload)
            if not ok:
                return [AgentMessage(kind="error", title="业务失败", content=reason, data=info)]
            try:
                from app.services.leave_service import leave_service

                leave = await leave_service.apply(
                    db, user_id, info["start_date"], info["end_date"], info["reason"]
                )
            except ValueError as exc:
                await db.rollback()
                return [AgentMessage(kind="error", title="业务失败", content=str(exc))]
            except Exception:
                await db.rollback()
                logger.exception("agent leave apply failed")
                return [AgentMessage(kind="error", title="系统异常", content="请假提交失败，请稍后重试")]
            self.sessions.add_fact(
                user_id, session_id,
                f"已提交请假：{info['start_date']} 至 {info['end_date']}（{info['total_days']}天）",
            )
            return [AgentMessage(
                kind="card", title="请假申请已提交",
                content=f"请假申请 #{leave.id} 已提交，共 {info['total_days']} 天，等待审批",
                data={**info, "leave_id": leave.id},
            )]
        if action == "repair_submit":
            ok, reason, info = self._precheck_repair(payload)
            if not ok:
                return [AgentMessage(kind="error", title="业务失败", content=reason, data=info)]
            try:
                repair = Repair(
                    user_id=user_id, role=payload.get("role") or "student",
                    location=info["location"], type=info["type"], description=info["description"],
                    status=RepairStatus.submitted.value,
                )
                db.add(repair)
                await db.commit()
                await db.refresh(repair)
            except Exception:
                await db.rollback()
                logger.exception("agent repair submit failed")
                return [AgentMessage(kind="error", title="系统异常", content="报修提交失败，请稍后重试")]
            self.sessions.add_fact(user_id, session_id, f"已提交报修：{info['location']}（{info['type']}）")
            return [AgentMessage(
                kind="card", title="报修提交成功",
                content=f"报修单 #{repair.id} 已提交：{info['location']}｜{info['type']}",
                data={**info, "repair_id": repair.id},
            )]
        if action == "reserve_classroom":
            params = {
                "classroom": str(payload["classroom_id"]), "week": str(payload["week"]),
                "day_of_week": str(payload["day_of_week"]), "period": payload["period"],
                "reason": payload["reason"],
            }
            ok, reason, info = await self._precheck_reserve(params, db)
            if not ok:
                return [AgentMessage(kind="error", title="业务失败", content=reason, data=info)]
            try:
                reservation = ClassroomReservation(
                    classroom_id=info["classroom_id"], week=info["week"], day_of_week=info["day_of_week"],
                    period=info["period"], user_id=user_id, user_role=payload.get("role") or "student",
                    reason=info["reason"], status="已预约",
                )
                db.add(reservation)
                await db.commit()
                await db.refresh(reservation)
            except IntegrityError:
                await db.rollback()
                return [AgentMessage(kind="error", title="业务失败", content="该时段已被其他人预约")]
            except Exception:
                await db.rollback()
                logger.exception("agent reserve classroom failed")
                return [AgentMessage(kind="error", title="系统异常", content="预约失败，请稍后重试")]
            self.sessions.add_fact(
                user_id, session_id,
                f"已预约教室：{info['classroom']}（第{info['week']}周 "
                f"{WEEKDAY_CN[info['day_of_week'] - 1]} {info['period']}节）",
            )
            return [AgentMessage(
                kind="card", title="预约成功",
                content=f"已预约 {info['classroom']}：第{info['week']}周 "
                        f"{WEEKDAY_CN[info['day_of_week'] - 1]} {info['period']}节",
                data=info,
            )]
        return [AgentMessage(kind="error", content="未知的确认动作")]

    async def _resolve_schedule(self, course: str, student_id: str, db) -> tuple[int | None, str]:
        """把用户说的课程名（含简称/口语名）解析为课程序号，返回 (schedule_id, 提示)。
        匹配失败或歧义时，提示给出候选课程，便于用户确认。"""
        course = (course or "").strip()
        if course.isdigit():
            sid = int(course)
            row = (await db.execute(select(Schedule.id).where(Schedule.id == sid))).scalar_one_or_none()
            return (sid, "") if row else (None, "课表记录不存在")
        stu = (await db.execute(select(Student).where(Student.id == student_id))).scalar_one_or_none()
        if not stu or not stu.class_id:
            return None, ""
        rows = (await db.execute(
            select(Schedule.id, Subject.name, Subject.type)
            .join(Subject, Schedule.subject_id == Subject.id)
            .where(Schedule.class_id == stu.class_id)
        )).all()
        if not course:
            return None, self._course_hint(rows)
        scored: list[tuple[float, int, str]] = []
        for sid, name, subj_type in rows:
            score = self._course_score(course, name)
            if score >= 2.0:
                scored.append((score, sid, name))
        if scored:
            best = max(s for s, _, _ in scored)
            top = [(sid, name) for s, sid, name in scored if s == best]
            if len(top) == 1:
                return top[0][0], ""
            names = sorted({name for _, name in top})
            return None, f"课程有多个匹配（{'、'.join(names)}），请说完整课程名"
        return None, self._course_hint(rows)

    @staticmethod
    def _course_score(query: str, name: str) -> float:
        """课程名贴合度：精确 > 双向包含 > 最长公共子串。"""
        if not query:
            return 0.0
        if query == name or query.upper() == name.upper():
            return 100.0
        if query in name or name in query:
            return 90.0
        return float(ActionExecutor._lcs_len(query, name))

    @staticmethod
    def _lcs_len(a: str, b: str) -> int:
        n, m = len(a), len(b)
        dp = [[0] * (m + 1) for _ in range(n + 1)]
        best = 0
        for i in range(1, n + 1):
            ai = a[i - 1]
            for j in range(1, m + 1):
                if ai == b[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                    best = max(best, dp[i][j])
        return best

    @staticmethod
    def _course_hint(rows) -> str:
        """无可匹配课程时，列出该班级可选的限选/选修课。"""
        names = sorted({name for _, name, subj_type in rows if subj_type != SubjectType.compulsory})
        if not names:
            return "该班级当前没有可选的限选/选修课程"
        return "可选课程有：" + "、".join(names)

    @staticmethod
    def _norm_date(value: str) -> date | None:
        if not value:
            return None
        key = str(value).strip()
        if key in _RELATIVE_DAY:
            return date.today() + timedelta(days=_RELATIVE_DAY[key])
        try:
            return date.fromisoformat(key)
        except ValueError:
            pass
        m = re.match(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?", key)
        if m:
            try:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                return None
        return None

    def _precheck_leave(self, params: dict) -> tuple[bool, str, dict]:
        start = self._norm_date(params.get("start_date", ""))
        end = self._norm_date(params.get("end_date", "")) or start  # 未指定结束日期默认单天
        reason = (params.get("reason") or "").strip()
        if not start or not end:
            return False, "请告诉我请假的开始和结束日期（格式：2026-08-05）", {}
        if end < start:
            return False, "结束日期不能早于开始日期", {}
        if start < date.today():
            return False, "请假开始日期不能早于今天", {}
        if not reason:
            return False, "请补充请假原因", {}
        info = {
            "start_date": start.isoformat(), "end_date": end.isoformat(),
            "total_days": (end - start).days + 1, "reason": reason,
        }
        return True, "预检通过，确认后提交请假申请（按天数进入辅导员/学院审批）", info

    def _precheck_repair(self, params: dict) -> tuple[bool, str, dict]:
        location = (params.get("location") or "").strip()
        rtype = (params.get("type") or "").strip()
        description = (params.get("description") or "").strip()
        if not location:
            return False, "请告诉我报修地点", {}
        if rtype not in REPAIR_TYPES:
            return False, f"报修类型需为：{' / '.join(sorted(REPAIR_TYPES))}", {}
        if not description:
            return False, "请描述具体问题", {}
        info = {"location": location, "type": rtype, "description": description}
        return True, "预检通过，确认后提交报修单", info

    async def _resolve_classroom(self, classroom: str, db) -> Classroom | None:
        classroom = (classroom or "").strip()
        if not classroom:
            return None
        if classroom.isdigit():
            return (await db.execute(
                select(Classroom).where(Classroom.id == int(classroom))
            )).scalar_one_or_none()
        rows = (await db.execute(
            select(Classroom).where(Classroom.name.contains(classroom))
        )).scalars().all()
        for row in rows:
            if row.name.upper() == classroom.upper():
                return row
        return rows[0] if len(rows) == 1 else None

    async def _precheck_reserve(self, params: dict, db) -> tuple[bool, str, dict]:
        classroom = await self._resolve_classroom(params.get("classroom", ""), db)
        if classroom is None:
            return False, "没找到要预约的教室，请提供教室名（如 D101）或教室 ID", {}
        try:
            week = int(params.get("week", ""))
            day = int(params.get("day_of_week", ""))
        except (TypeError, ValueError):
            return False, "请提供预约周次（1-52）和星期（1-7）", {}
        period = (params.get("period") or "").strip().replace("节", "").strip()
        reason = (params.get("reason") or "").strip()
        if not (1 <= week <= 52 and 1 <= day <= 7):
            return False, "周次需在 1-52，星期需在 1-7", {}
        if not period:
            return False, "请提供预约节次（如 1-2）", {}
        try:
            p1, p2 = period.split("-")
            p1, p2 = int(p1), int(p2)
            if not (1 <= p1 <= 12 and 1 <= p2 <= 12) or p1 > p2:
                return False, "节次需在 1-12 之间且起止有序", {}
        except ValueError:
            return False, f"节次格式不正确：{period}", {}
        if not reason:
            return False, "请补充预约理由", {}
        rows = (await db.execute(
            select(Schedule, Subject)
            .join(Subject, Schedule.subject_id == Subject.id)
            .where(Schedule.classroom_id == classroom.id, Schedule.day_of_week == day)
        )).all()
        for s, subj in rows:
            if is_week_matched(week, s.weeks) and is_period_overlap(period, s.period):
                return False, f"该时段有课程安排：{subj.name}（{WEEKDAY_CN[day - 1]} {s.period}节）", {}
        dup = (await db.execute(
            select(ClassroomReservation).where(
                ClassroomReservation.classroom_id == classroom.id,
                ClassroomReservation.week == week,
                ClassroomReservation.day_of_week == day,
                ClassroomReservation.period == period,
                ClassroomReservation.status == "已预约",
            )
        )).scalar_one_or_none()
        if dup:
            return False, "该时段已被其他人预约", {}
        info = {
            "classroom": classroom.name, "classroom_id": classroom.id,
            "building": classroom.building, "capacity": classroom.capacity,
            "week": week, "day_of_week": day, "period": period, "reason": reason,
        }
        return True, "预检通过，确认后提交预约", info

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
