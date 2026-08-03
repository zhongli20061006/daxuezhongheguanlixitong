# 教师端 Agent 工作流 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让教师通过自然语言完成查班级课表、查学生名单、查我的监考、成绩录入（确认流）四个工作流。

**Architecture:** 完全复用现有 Agent 分层（intent 解析 → ActionExecutor handler → ConfirmationStore 确认流），只新增 3 个意图/处理器与 1 个共享成绩写入服务；提示词按角色注入，权限仍由执行层 `_allowed` 强制。

**Tech Stack:** Python 3.13 / FastAPI / SQLAlchemy async / pytest（SQLite 内存库）/ Vue 3 + Element Plus。

**Spec:** `docs/superpowers/specs/2026-08-03-teacher-agent-workflows-design.md`

**约定：**
- 测试命令在项目根目录执行：`.venv\Scripts\python.exe -m pytest tests/<file> -q`
- 回归基线：现有 108 个测试全绿
- git 命令必须带 `-c safe.directory="D:/DjangoProject/学生管理系统（实验）"`，且写入 `.git` 需要提权（沙箱限制）；每个任务结束提交一次

---

## Task 1: 意图与角色感知提示词

**Files:**
- Modify: `app/services/agent/intent.py`
- Modify: `app/services/agent/prompts.py`
- Modify: `app/api/agent.py`
- Test: `tests/test_agent_intent.py`

- [ ] **Step 1: 写失败测试**（追加到 `tests/test_agent_intent.py` 末尾）

```python
def test_rules_query_class_schedule():
    intent = match_rules("查一下2024级计算机科学1班的课表")
    assert intent is not None
    assert intent.intent == IntentType.query_class_schedule
    assert "2024级计算机科学1班" in intent.params["class"]


def test_rules_query_students():
    intent = match_rules("查一下5班有哪些学生")
    assert intent is not None
    assert intent.intent == IntentType.query_students
    assert intent.params["class"] == "5班"


def test_rules_score_entry_beats_query_scores():
    intent = match_rules("把张三的高数成绩录成90分")
    assert intent is not None
    assert intent.intent == IntentType.score_entry
    assert intent.need_confirm is True
    assert intent.params["score"] == "90"
    assert intent.params["score_type"] == "期末"


def test_rules_query_scores_still_works():
    intent = match_rules("查一下张三的成绩")
    assert intent is not None
    assert intent.intent == IntentType.query_scores


class CaptureLLM(FakeLLM):
    def __init__(self):
        super().__init__(result={"intents": [{"intent": "chat", "params": {}, "confidence": 0.3}]})
        self.prompt = None

    async def extract_json(self, messages):
        self.prompt = messages[0]["content"]
        return self.result


@pytest.mark.asyncio
async def test_resolve_prompt_is_role_aware():
    resolver = IntentResolver(CaptureLLM())
    await resolver.resolve("查一下5班的课表", role="teacher")
    assert "query_class_schedule" in resolver.llm.prompt
    assert "score_entry" in resolver.llm.prompt
    await resolver.resolve("查一下5班的课表", role="student")
    assert "query_class_schedule" not in resolver.llm.prompt
    assert "score_entry" not in resolver.llm.prompt


@pytest.mark.asyncio
async def test_resolve_role_cache_key_isolated():
    llm = CaptureLLM()
    resolver = IntentResolver(llm)
    await resolver.resolve("查一下5班的课表", role="teacher")
    await resolver.resolve("查一下5班的课表", role="student")
    assert llm.calls == 2
```

（`test_agent_intent.py` 顶部已导入 `IntentResolver`、`IntentType`、`match_rules`、`FakeLLM`、`pytest`；`FakeLLM.calls` 已在类中自增。）

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_intent.py -q`
Expected: 新增用例 FAIL（`IntentType.query_class_schedule` 不存在等）

- [ ] **Step 3: 实现**

`app/services/agent/intent.py`：

```python
class IntentType(str, Enum):
    navigate = "navigate"
    query_schedule = "query_schedule"
    query_class_schedule = "query_class_schedule"
    query_students = "query_students"
    study_plan = "study_plan"
    enroll = "enroll"
    drop = "drop"
    query_classroom = "query_classroom"
    reserve_classroom = "reserve_classroom"
    repair_submit = "repair_submit"
    leave_apply = "leave_apply"
    approve_leave = "approve_leave"
    query_scores = "query_scores"
    query_notifications = "query_notifications"
    query_exams = "query_exams"
    score_entry = "score_entry"
    chat = "chat"


WRITE_INTENTS = frozenset({
    IntentType.enroll, IntentType.drop, IntentType.reserve_classroom,
    IntentType.repair_submit, IntentType.leave_apply, IntentType.approve_leave,
    IntentType.score_entry,
})
```

`RULE_TABLE` 调整（`query_class_schedule` 插在 `query_schedule` 之前；`score_entry` 插在 `query_scores` 之前；`query_students` 插入同区段）：

```python
RULE_TABLE: list[tuple[IntentType, list[str], str | None]] = [
    (IntentType.study_plan, ["学习方案", "学习计划", "怎么学", "复习计划"], None),
    (IntentType.query_class_schedule, ["班级课表", "班的课表", "查班级课表"], None),
    (IntentType.query_schedule, ["上什么课", "课程安排", "课表"], None),
    (IntentType.query_classroom, ["空教室", "教室可用", "查教室"], None),
    (IntentType.query_exams, ["考试", "监考"], None),
    (IntentType.score_entry, ["录成绩", "录入成绩", "成绩录", "打分", "录分"], None),
    (IntentType.query_scores, ["成绩", "绩点"], None),
    (IntentType.query_notifications, ["通知", "未读"], None),
    (IntentType.reserve_classroom, ["预约教室", "借教室", "订教室", "申请教室"], None),
    (IntentType.drop, ["退课", "退选", "不上了"], r"(?:退课|退选)\s*([^\s，。,.！!？?]+)"),
    (IntentType.enroll, ["选课", "选这门", "报名", "选修", "帮我选", "要选"], r"(?:选|报)(?:修|名)?\s*([^\s，。,.！!？?]+)"),
    (IntentType.query_students, ["学生名单", "有哪些学生", "查学生"], None),
    (IntentType.repair_submit, ["报修", "修一下", "后勤", "东西坏了"], None),
    (IntentType.approve_leave, ["审批", "批准", "驳回", "同意请假"], None),
    (IntentType.leave_apply, ["请假", "休假申请"], None),
    (IntentType.study_plan, ["其他的呢", "其他科目", "剩下的", "还有呢"], None),
]
```

新增参数抽取函数（放在 `_extract_approve_params` 之后）：

```python
def _extract_class_schedule_params(text: str) -> dict[str, str]:
    """规则兜底：抽取班级名（到“班”字为止，去掉前导动词）。"""
    params: dict[str, str] = {}
    cleaned = re.sub(r"^(?:请|帮我|给我|查一下|查|看看|看)", "", text.strip())
    m = re.search(r"([\u4e00-\u9fa5A-Za-z0-9]{1,20}?班)", cleaned)
    if m:
        params["class"] = m.group(1).strip()
    return params


def _extract_students_params(text: str) -> dict[str, str]:
    """规则兜底：抽取班级/学号（姓名由 LLM 或追问提供）。"""
    params: dict[str, str] = {}
    cleaned = re.sub(r"^(?:请|帮我|给我|查一下|查|看看|看)", "", text.strip())
    m = re.search(r"([\u4e00-\u9fa5A-Za-z0-9]{1,20}?班)", cleaned)
    if m:
        params["class"] = m.group(1).strip()
    m = re.search(r"([A-Z]\d{6,7})", text)
    if m:
        params["student_id"] = m.group(1)
    return params


def _extract_score_params(text: str) -> dict[str, str]:
    """规则兜底：抽取分数与成绩类型（学生/课程由 LLM 或追问提供）。"""
    params: dict[str, str] = {}
    m = re.search(r"(\d{1,3}(?:\.\d+)?)\s*分", text)
    if m:
        params["score"] = m.group(1)
    if "平时" in text:
        params["score_type"] = "平时"
    else:
        params["score_type"] = "期末"
    return params
```

`extract_params_for` 增加分支：

```python
def extract_params_for(intent_type: "IntentType", text: str) -> dict[str, str]:
    """按意图类型抽取参数，供动作层/多轮补全复用。"""
    if intent_type == IntentType.query_classroom:
        return _extract_classroom_params(text)
    if intent_type == IntentType.query_class_schedule:
        return _extract_class_schedule_params(text)
    if intent_type == IntentType.query_students:
        return _extract_students_params(text)
    if intent_type == IntentType.score_entry:
        return _extract_score_params(text)
    if intent_type == IntentType.leave_apply:
        return _extract_leave_params(text)
    if intent_type == IntentType.repair_submit:
        return _extract_repair_params(text)
    if intent_type == IntentType.reserve_classroom:
        return _extract_reserve_params(text)
    if intent_type == IntentType.approve_leave:
        return _extract_approve_params(text)
    return {}
```

`match_rules` 的 RULE_TABLE 循环内增加参数抽取分支：

```python
                if intent == IntentType.leave_apply:
                    params = _extract_leave_params(lowered)
                elif intent == IntentType.query_classroom:
                    params = _extract_classroom_params(lowered)
                elif intent == IntentType.query_class_schedule:
                    params = _extract_class_schedule_params(lowered)
                elif intent == IntentType.query_students:
                    params = _extract_students_params(lowered)
                elif intent == IntentType.score_entry:
                    params = _extract_score_params(lowered)
                elif intent == IntentType.repair_submit:
                    params = _extract_repair_params(lowered)
                elif intent == IntentType.reserve_classroom:
                    params = _extract_reserve_params(lowered)
                elif intent == IntentType.approve_leave:
                    params = _extract_approve_params(lowered)
                elif pattern:
                    m = re.search(pattern, lowered)
                    if m:
                        params["course"] = m.group(1).strip()
```

`IntentResolver` 改为角色感知（缓存 key 为 `(role, text)`）：

```python
    async def resolve(self, text: str, role: str = "student") -> tuple[list[Intent], str]:
        now = time.time()
        cache_key = (role, text)
        cached = self._cache.get(cache_key)
        if cached and now - cached[0] <= self.cache_ttl:
            return cached[1], "cache"

        for _ in range(2):  # JSON 解析失败重试一次
            try:
                data = await self.llm.extract_json([
                    {"role": "system", "content": intent_system_prompt(role)},
                    {"role": "user", "content": text},
                ])
                intents = self._parse_llm(data)
                if intents:
                    if all(i.intent == IntentType.chat for i in intents):
                        rule = match_rules(text)
                        if rule:
                            self._put(cache_key, [rule], now)
                            return [rule], "rules"
                    for intent in intents:
                        if intent.intent in WRITE_INTENTS:
                            for key, value in extract_params_for(intent.intent, text).items():
                                if value:
                                    intent.params[key] = value
                    self._put(cache_key, intents, now)
                    return intents, "llm"
            except (OllamaUnavailable, OllamaTimeout, OllamaBusy):
                break
            except (ValueError, ValidationError):
                continue

        rule = match_rules(text)
        if rule:
            intents = [rule]
            self._put(cache_key, intents, now)
            return intents, "rules"
        return [Intent(intent=IntentType.chat, confidence=0.3)], "fallback"

    def _put(self, key: tuple[str, str], intents: list[Intent], now: float) -> None:
        if len(self._cache) >= self.cache_size:
            oldest = min(self._cache, key=lambda k: self._cache[k][0])
            self._cache.pop(oldest, None)
        self._cache[key] = (now, intents)
```

`intent.py` 顶部 import 改为：

```python
from app.services.agent.prompts import intent_system_prompt
```

`app/services/agent/prompts.py` 末尾追加：

```python
TEACHER_INTENT_PROMPT = (
    "教师角色额外支持的意图：\n"
    "- query_class_schedule：查班级课表 params.class（班级名，如“2024级计算机科学1班”或“1班”）\n"
    "- query_students：查学生名单 params.class/name/student_id（三选一）\n"
    "- score_entry：录入成绩 params.student（姓名或学号）/course（课程名）/score（0-100 数字）"
    "/score_type（平时或期末，默认期末）\n"
    '示例1：用户说“查一下2024级计算机科学1班的课表”→'
    '{"intents":[{"intent":"query_class_schedule","params":{"class":"2024级计算机科学1班"},"confidence":0.9}]}\n'
    '示例2：用户说“把张三的高数成绩录成90分”→'
    '{"intents":[{"intent":"score_entry","params":{"student":"张三","course":"高等数学","score":"90","score_type":"期末"},"confidence":0.9}]}\n'
    '示例3：用户说“查一下5班有哪些学生”→'
    '{"intents":[{"intent":"query_students","params":{"class":"5班"},"confidence":0.9}]}\n'
)


def intent_system_prompt(role: str = "student") -> str:
    """按角色组装意图解析提示词；角色差异只影响提示，权限仍由执行层强制。"""
    prompt = BASE_SYSTEM_PROMPT + "\n\n" + INTENT_TASK_PROMPT
    if role == "teacher":
        prompt += "\n\n" + TEACHER_INTENT_PROMPT
    return prompt
```

`app/api/agent.py` 中调用点改为：

```python
        intents, source = await resolver.resolve(req.message, role)
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_intent.py -q`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add app/services/agent/intent.py app/services/agent/prompts.py app/api/agent.py tests/test_agent_intent.py
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "feat(agent): teacher intents and role-aware intent prompt"
```

---

## Task 2: 权限矩阵 + 查班级课表

**Files:**
- Modify: `app/services/agent/actions.py`
- Test: `tests/test_agent_actions.py`

- [ ] **Step 1: 写失败测试**（追加到 `tests/test_agent_actions.py` 末尾）

```python
@pytest.mark.asyncio
async def test_teacher_query_class_schedule_card(db, test_engine):
    await _seed(db, test_engine)
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.query_class_schedule, params={"class": "测试班"}),
        "T10001", "teacher", "s", db,
    )
    assert msgs[0].kind == "card"
    assert msgs[0].data["schedule"]
    assert msgs[0].data["class"] == "测试班"


@pytest.mark.asyncio
async def test_student_blocked_from_class_schedule(db):
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.query_class_schedule, params={"class": "测试班"}),
        "S2024001", "student", "s", db,
    )
    assert msgs[0].kind == "error"


@pytest.mark.asyncio
async def test_query_class_schedule_missing_class(db):
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.query_class_schedule, params={}),
        "T10001", "teacher", "s", db,
    )
    assert msgs[0].kind == "error"


@pytest.mark.asyncio
async def test_query_class_schedule_ambiguous_class(db, test_engine):
    await _seed(db, test_engine)
    db.add(StudentClass(id=2, name="测试班2", major="软件工程", grade=2024, advisor_id=1))
    await db.commit()
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.query_class_schedule, params={"class": "测试班"}),
        "T10001", "teacher", "s", db,
    )
    assert msgs[0].kind == "error"
    assert "多个班级" in msgs[0].content
```

（`test_agent_actions.py` 顶部已导入 `StudentClass`、`Intent`、`IntentType`、`_seed`、`_executor`。）

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_actions.py -q`
Expected: 新增用例 FAIL（handler 不存在）

- [ ] **Step 3: 实现**（`app/services/agent/actions.py`）

权限矩阵：

```python
NOT_FOR_STUDENT = frozenset({
    IntentType.approve_leave, IntentType.query_class_schedule,
    IntentType.query_students, IntentType.score_entry,
})
```

新增班级解析与 handler（放在 `_handle_query_schedule` 之后）：

```python
    async def _resolve_class(self, class_ref: str, db: AsyncSession):
        """按班级名精确/包含匹配；唯一命中才返回，多义让用户确认。"""
        from app.models import StudentClass

        if not class_ref or not class_ref.strip():
            return None, "请提供班级名称，例如“2024级计算机科学1班”或“1班”"
        ref = class_ref.strip()
        rows = (await db.execute(
            select(StudentClass).order_by(StudentClass.id)
        )).scalars().all()
        exact = [c for c in rows if c.name == ref]
        if exact:
            return exact[0], None
        matches = [c for c in rows if ref in c.name or c.name in ref]
        if len(matches) == 1:
            return matches[0], None
        if len(matches) > 1:
            names = "、".join(c.name for c in matches)
            return None, f"找到多个班级（{names}），请提供更完整的班级名"
        return None, f"没找到班级“{ref}”"

    async def _handle_query_class_schedule(self, intent, user_id, role, session_id, db):
        from app.models import Classroom, Schedule, Subject, Teacher
        from app.services.agent import AgentMessage

        cls, err = await self._resolve_class(intent.params.get("class"), db)
        if err:
            return [AgentMessage(kind="error", title="业务失败", content=err)]
        rows = (await db.execute(
            select(Schedule, Subject, Teacher, Classroom)
            .join(Subject, Schedule.subject_id == Subject.id)
            .join(Teacher, Schedule.teacher_id == Teacher.id)
            .join(Classroom, Schedule.classroom_id == Classroom.id)
            .where(Schedule.class_id == cls.id)
            .order_by(Schedule.day_of_week, Schedule.period)
        )).all()
        items = [{
            "day_of_week": s.day_of_week,
            "course": subj.name,
            "teacher": t.name,
            "classroom": c.name,
            "period": s.period,
            "weeks": s.weeks,
        } for s, subj, t, c in rows]
        if not items:
            return [AgentMessage(
                kind="card", title=f"{cls.name} 课表",
                content="暂无课程安排", data={"schedule": [], "class": cls.name},
            )]
        return [AgentMessage(
            kind="card", title=f"{cls.name} 课表",
            content=f"共 {len(items)} 条课程安排", data={"schedule": items, "class": cls.name},
        )]
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_actions.py -q`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add app/services/agent/actions.py tests/test_agent_actions.py
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "feat(agent): teacher query class schedule"
```

---

## Task 3: 查学生名单

**Files:**
- Modify: `app/services/agent/actions.py`
- Test: `tests/test_agent_actions.py`

- [ ] **Step 1: 写失败测试**（追加到 `tests/test_agent_actions.py` 末尾）

```python
@pytest.mark.asyncio
async def test_teacher_query_students_by_class(db, test_engine):
    await _seed(db, test_engine)
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.query_students, params={"class": "测试班"}),
        "T10001", "teacher", "s", db,
    )
    assert msgs[0].kind == "card"
    assert msgs[0].data["students"][0]["student_id"] == "S2024001"


@pytest.mark.asyncio
async def test_teacher_query_students_by_name(db, test_engine):
    await _seed(db, test_engine)
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.query_students, params={"name": "测试学生"}),
        "T10001", "teacher", "s", db,
    )
    assert msgs[0].kind == "card"
    assert len(msgs[0].data["students"]) == 1


@pytest.mark.asyncio
async def test_query_students_missing_params(db):
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.query_students, params={}),
        "T10001", "teacher", "s", db,
    )
    assert msgs[0].kind == "text"


@pytest.mark.asyncio
async def test_student_blocked_from_query_students(db):
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.query_students, params={"class": "测试班"}),
        "S2024001", "student", "s", db,
    )
    assert msgs[0].kind == "error"
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_actions.py -q`
Expected: 新增用例 FAIL

- [ ] **Step 3: 实现**（`app/services/agent/actions.py`，放在 `_handle_query_class_schedule` 之后）

```python
    async def _handle_query_students(self, intent, user_id, role, session_id, db):
        from app.models import Student
        from app.services.agent import AgentMessage

        params = intent.params
        sid = (params.get("student_id") or "").strip()
        name = (params.get("name") or "").strip()
        class_ref = (params.get("class") or "").strip()
        if not (sid or name or class_ref):
            return [AgentMessage(
                kind="text",
                content="查学生名单需要班级、姓名或学号，例如“5班有哪些学生”",
            )]
        if sid:
            rows = (await db.execute(
                select(Student).where(Student.id == sid)
            )).scalars().all()
        elif name:
            rows = (await db.execute(
                select(Student).where(Student.name == name)
            )).scalars().all()
        else:
            cls, err = await self._resolve_class(class_ref, db)
            if err:
                return [AgentMessage(kind="error", title="业务失败", content=err)]
            rows = (await db.execute(
                select(Student).where(Student.class_id == cls.id).order_by(Student.id)
            )).scalars().all()
        if not rows:
            return [AgentMessage(
                kind="card", title="学生名单",
                content="未找到学生", data={"students": []},
            )]
        students = [{"student_id": s.id, "name": s.name, "class_id": s.class_id} for s in rows]
        if len(students) > 50:
            shown, note = students[:50], f"共 {len(students)} 人，仅显示前 50 人"
        else:
            shown, note = students, f"共 {len(students)} 人"
        return [AgentMessage(
            kind="card", title="学生名单", content=note, data={"students": shown},
        )]
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_actions.py -q`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add app/services/agent/actions.py tests/test_agent_actions.py
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "feat(agent): teacher query students"
```

---

## Task 4: 成绩写入服务抽取 + API 复用

**Files:**
- Create: `app/services/score_service.py`
- Modify: `app/api/score.py`
- Test: `tests/test_score_service.py`

- [ ] **Step 1: 写失败测试**（新建 `tests/test_score_service.py`）

```python
"""成绩写入服务：插入/更新、总评自动计算，以及 API 手动录入回归。"""
import pytest
from sqlalchemy import select

from app.models import (
    Classroom, CourseCapacity, CourseSelection, Schedule, Score, ScoreType,
    Student, StudentClass, Subject, SubjectType, SystemConfig, Teacher,
)
from app.services.score_service import auto_calculate_total_if_ready, record_score


async def _seed_score(db, test_engine):
    from tests.test_agent_actions import _cleanup

    await _cleanup(test_engine)
    db.add_all([
        StudentClass(id=1, name="测试班", major="计算机", grade=2024, advisor_id=1),
        Teacher(id=1, name="张老师", job_number="T10001", department="计算机", title="教授", is_college_admin=False),
        Subject(id=1, name="高等数学", credit=5.0, type=SubjectType.compulsory),
        Classroom(id=1, name="D101", capacity=60, building="D", has_projector=False),
        Student(id="S2024001", name="测试学生", class_id=1),
    ])
    await db.flush()
    db.add(Schedule(
        id=1, teacher_id=1, subject_id=1, class_id=1, classroom_id=1,
        weeks="1-18", day_of_week=1, period="1-2", semester="2024-2025-1",
    ))
    db.add(CourseCapacity(schedule_id=1, enrolled=1, capacity=30))
    db.add(CourseSelection(student_id="S2024001", schedule_id=1, status=1))
    await db.commit()


@pytest.mark.asyncio
async def test_record_score_insert_then_update(db, test_engine):
    await _seed_score(db, test_engine)
    inserted, updated = await record_score(
        db, schedule_id=1, student_id="S2024001", score=88, score_type="期末",
    )
    assert (inserted, updated) == (1, 0)
    inserted2, updated2 = await record_score(
        db, schedule_id=1, student_id="S2024001", score=95, score_type="期末",
    )
    assert (inserted2, updated2) == (0, 1)
    rows = (await db.execute(select(Score))).scalars().all()
    assert len(rows) == 1
    assert rows[0].score == 95


@pytest.mark.asyncio
async def test_auto_calculate_total_when_both_parts_ready(db, test_engine):
    await _seed_score(db, test_engine)
    await record_score(db, schedule_id=1, student_id="S2024001", score=80, score_type="平时")
    await record_score(db, schedule_id=1, student_id="S2024001", score=90, score_type="期末")
    await db.flush()
    calculated = await auto_calculate_total_if_ready(db, 1)
    assert calculated == 1
    totals = (await db.execute(
        select(Score).where(Score.score_type == ScoreType.total)
    )).scalars().all()
    assert len(totals) == 1


@pytest.mark.asyncio
async def test_manual_score_endpoint_regression(client, db, test_engine):
    from app.deps import get_current_user
    from app.main import app

    await _seed_score(db, test_engine)
    app.dependency_overrides[get_current_user] = lambda: {
        "username": "T10001", "role": "teacher", "role_id": "T10001",
    }
    try:
        resp = await client.post("/scores/manual", json={
            "schedule_id": 1,
            "score_type": "期末",
            "scores": [{"student_id": "S2024001", "score": 87}],
        })
        assert resp.status_code == 200, resp.text
        assert resp.json()["inserted"] == 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)
```

（已核对 `app/schemas/score.py`：`ManualScoreRequest(schedule_id, score_type, scores: list[ScoreEntry(student_id, score)])`，与测试请求一致。）

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_score_service.py -q`
Expected: 新增用例 FAIL（`app.services.score_service` 不存在）

- [ ] **Step 3: 实现**

新建 `app/services/score_service.py`：

```python
"""成绩写入服务：API 与智能体共用，避免录入/总评逻辑漂移。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CourseSelection, Score, ScoreType
from app.utils.gpa_calculator import score_to_gpa

# 总评计算权重：平时占20%，期末占80%
DAILY_WEIGHT = 0.2
FINAL_WEIGHT = 0.8


async def record_score(
    db: AsyncSession, *,
    schedule_id: int, student_id: str, score: float, score_type: str | ScoreType,
) -> tuple[int, int]:
    """录入或更新一条成绩（平时/期末），返回 (inserted, updated)。"""
    st = score_type if isinstance(score_type, ScoreType) else ScoreType(score_type)
    existing = (await db.execute(
        select(Score).where(
            Score.student_id == student_id,
            Score.schedule_id == schedule_id,
            Score.score_type == st,
            Score.attempt == 1,
        )
    )).scalar_one_or_none()
    if existing:
        existing.score = score
        existing.gpa = float(score_to_gpa(score))
        return 0, 1
    db.add(Score(
        student_id=student_id,
        schedule_id=schedule_id,
        score=score,
        gpa=float(score_to_gpa(score)),
        score_type=st,
        attempt=1,
    ))
    return 1, 0


async def auto_calculate_total_if_ready(db: AsyncSession, schedule_id: int) -> int:
    """该课表所有学生平时+期末齐全时计算总评，返回计算人数。"""
    enrolled_ids = [row[0] for row in (await db.execute(
        select(CourseSelection.student_id).where(
            CourseSelection.schedule_id == schedule_id,
            CourseSelection.status == 1,
        )
    )).all()]
    if not enrolled_ids:
        return 0
    daily_map = {s.student_id: s for s in (await db.execute(
        select(Score).where(
            Score.schedule_id == schedule_id,
            Score.student_id.in_(enrolled_ids),
            Score.score_type == ScoreType.daily,
            Score.attempt == 1,
        )
    )).scalars().all()}
    final_map = {s.student_id: s for s in (await db.execute(
        select(Score).where(
            Score.schedule_id == schedule_id,
            Score.student_id.in_(enrolled_ids),
            Score.score_type == ScoreType.final,
            Score.attempt == 1,
        )
    )).scalars().all()}
    total_map = {s.student_id: s for s in (await db.execute(
        select(Score).where(
            Score.schedule_id == schedule_id,
            Score.student_id.in_(enrolled_ids),
            Score.score_type == ScoreType.total,
            Score.attempt == 1,
        )
    )).scalars().all()}
    calculated = 0
    for sid in enrolled_ids:
        daily, final = daily_map.get(sid), final_map.get(sid)
        if daily and final:
            total_gpa = round(float(daily.gpa) * DAILY_WEIGHT + float(final.gpa) * FINAL_WEIGHT, 1)
            existing = total_map.get(sid)
            if existing:
                existing.gpa = total_gpa
            else:
                db.add(Score(
                    student_id=sid, schedule_id=schedule_id, score=None,
                    gpa=total_gpa, score_type=ScoreType.total, attempt=1,
                ))
            calculated += 1
    return calculated
```

`app/api/score.py` 改造：

```python
from app.services.score_service import (
    DAILY_WEIGHT, FINAL_WEIGHT, auto_calculate_total_if_ready, record_score,
)
```

- 删除文件内的 `DAILY_WEIGHT`、`FINAL_WEIGHT` 常量定义和 `_auto_calculate_total_if_ready` 函数定义
- `manual_score` 内录入循环改为：

```python
    for entry in req.scores:
        if entry.score < 0 or entry.score > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"学生 {entry.student_id} 的分数 {entry.score} 超出 0-100 范围",
            )
        sel_result = await db.execute(
            select(CourseSelection).where(
                CourseSelection.student_id == entry.student_id,
                CourseSelection.schedule_id == req.schedule_id,
                CourseSelection.status == 1,
            )
        )
        if not sel_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"学生 {entry.student_id} 未选此课程",
            )
        inserted_i, updated_i = await record_score(
            db, schedule_id=req.schedule_id, student_id=entry.student_id,
            score=entry.score, score_type=score_type,
        )
        inserted += inserted_i
        updated += updated_i
```

- `manual_score` 中 `calculated = await _auto_calculate_total_if_ready(req.schedule_id, db)` → `calculated = await auto_calculate_total_if_ready(db, req.schedule_id)`
- `import_scores` 中 `calculated = await _auto_calculate_total_if_ready(schedule_id, db)` → `calculated = await auto_calculate_total_if_ready(db, schedule_id)`
- `calculate_total` 中 `calculated = await _auto_calculate_total_if_ready(schedule_id, db)` → `calculated = await auto_calculate_total_if_ready(db, schedule_id)`
- `_recalc_total` 保留，但其 `DAILY_WEIGHT/FINAL_WEIGHT` 引用来自 service import（无需改动）

- [ ] **Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_score_service.py tests/test_agent_actions.py tests/test_agent_api.py -q`
Expected: 全部 PASS（含原有 Agent 测试回归）

- [ ] **Step 5: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add app/services/score_service.py app/api/score.py tests/test_score_service.py
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "refactor(score): extract shared score write service"
```

---

## Task 5: 成绩录入动作与确认流

**Files:**
- Modify: `app/services/agent/actions.py`
- Test: `tests/test_agent_actions.py`
- Test: `tests/test_agent_api.py`

- [ ] **Step 1: 写失败测试**

追加到 `tests/test_agent_actions.py`：

```python
@pytest.mark.asyncio
async def test_score_entry_blocked_for_student(db):
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.score_entry, params={
            "student": "S2024001", "course": "人工智能实战", "score": "90",
        }),
        "S2024001", "student", "s", db,
    )
    assert msgs[0].kind == "error"


@pytest.mark.asyncio
async def test_score_entry_missing_params_asks(db):
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.score_entry, params={"score": "90"}),
        "T10001", "teacher", "s", db,
    )
    assert msgs[0].kind == "text"
    assert "学生" in msgs[0].content


@pytest.mark.asyncio
async def test_score_entry_confirmation_then_execute(db, test_engine):
    await _seed(db, test_engine)
    db.add(CourseSelection(student_id="S2024001", schedule_id=1, status=1))
    await db.commit()
    executor = _executor()
    intent = Intent(intent=IntentType.score_entry, params={
        "student": "S2024001", "course": "人工智能实战", "score": "90", "score_type": "期末",
    }, need_confirm=True)
    msgs = await executor.execute(intent, "T10001", "teacher", "sess1", db)
    assert msgs[0].kind == "confirmation"
    token = msgs[0].confirm_token
    results = await executor.execute_confirm(
        executor.confirmations.consume("T10001", token), db
    )
    assert results[0].kind == "card"
    scores = (await db.execute(
        select(Score).where(Score.student_id == "S2024001")
    )).scalars().all()
    assert len(scores) == 1
    assert scores[0].score == 90
```

追加到 `tests/test_agent_api.py`（`_seed_agent_data` 已建 schedule id=1 为“人工智能实战”，课程归属教师 T10001）：

```python
class ScoreLLM(FakeLLM):
    async def extract_json(self, messages):
        return {"intents": [{
            "intent": "score_entry",
            "params": {
                "student": "测试学生", "course": "人工智能实战",
                "score": "90", "score_type": "期末",
            },
            "confidence": 0.9,
        }]}


@pytest.mark.asyncio
async def test_chat_score_entry_teacher_flow(client, db, test_engine, monkeypatch):
    """教师录入成绩：确认卡片 → 文本确认 → 落库。"""
    from app.api import agent as agent_api
    from app.deps import get_current_user
    from app.main import app

    await _seed_agent_data(db, test_engine)
    db.add(CourseSelection(student_id="S2024001", schedule_id=1, status=1))
    await db.commit()
    monkeypatch.setattr(agent_api.resolver, "llm", ScoreLLM())

    app.dependency_overrides[get_current_user] = lambda: {
        "username": "T10001", "role": "teacher", "role_id": "T10001",
    }
    try:
        resp = await client.post("/agent/chat", json={
            "message": "把测试学生的人工智能实战成绩录成90分",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "confirmation" in [m["kind"] for m in data["messages"]]
        sid = data["session_id"]

        resp2 = await client.post("/agent/chat", json={"session_id": sid, "message": "确认"})
        assert resp2.status_code == 200
        assert resp2.json()["source"] == "confirm"
        scores = (await db.execute(select(Score))).scalars().all()
        assert len(scores) == 1
        assert scores[0].score == 90
    finally:
        app.dependency_overrides.pop(get_current_user, None)
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_actions.py tests/test_agent_api.py -q`
Expected: 新增用例 FAIL（handler 不存在）

- [ ] **Step 3: 实现**（`app/services/agent/actions.py`）

```python
    async def _handle_score_entry(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        if role != "teacher":
            return [AgentMessage(kind="error", title="业务失败", content="仅教师可录入成绩")]
        params = intent.params
        missing = [k for k in ("student", "course", "score")
                   if not (params.get(k) or "").strip()]
        if missing:
            self.sessions.set_pending_write(user_id, session_id, intent.intent.value, params)
            return [AgentMessage(
                kind="text",
                content="请提供学生（姓名或学号）、课程和分数，例如“把张三的高数成绩录成90分”",
            )]
        ok, reason, info = await self._precheck_score_entry(params, user_id, db)
        if not ok:
            return [AgentMessage(kind="error", title="业务失败", content=reason, data=info)]
        self.sessions.clear_pending_write(user_id, session_id)
        token = self.confirmations.create(user_id, {
            "action": "score_entry",
            "schedule_id": info["schedule_id"],
            "student_id": info["student_id"],
            "score": info["score"],
            "score_type": info["score_type"],
            "user_id": user_id,
            "session_id": session_id,
        })
        return [AgentMessage(
            kind="confirmation", title="确认录入成绩",
            content=f"{info['student_name']} · {info['course']} · {info['score']}分（{info['score_type']}）",
            data=info, confirm_token=token,
        )]

    async def _precheck_score_entry(self, params, user_id, db):
        """预检查：分数范围、学生唯一、课程归属当前教师、学生已选课。"""
        from app.models import CourseSelection, Schedule, Student, Subject, Teacher

        score_raw = params.get("score")
        if isinstance(score_raw, str):
            score_raw = score_raw.strip()
        try:
            score = float(score_raw)
        except (TypeError, ValueError):
            return False, "分数必须是数字", {}
        if score < 0 or score > 100:
            return False, "分数必须在 0-100 之间", {}
        teacher = (await db.execute(
            select(Teacher).where(Teacher.job_number == user_id)
        )).scalar_one_or_none()
        if not teacher:
            return False, "教师信息不存在", {}
        student_ref = (params.get("student") or "").strip()
        if student_ref.isdigit() or student_ref.upper().startswith("S"):
            student = (await db.execute(
                select(Student).where(Student.id == student_ref)
            )).scalar_one_or_none()
        else:
            student = (await db.execute(
                select(Student).where(Student.name == student_ref)
            )).scalar_one_or_none()
        if not student:
            return False, f"找不到学生“{student_ref}”", {}
        course_ref = (params.get("course") or "").strip()
        rows = (await db.execute(
            select(Schedule, Subject)
            .join(Subject, Schedule.subject_id == Subject.id)
            .where(Schedule.teacher_id == teacher.id)
        )).all()
        matched = [r for r in rows if r.Subject.name == course_ref] or [
            r for r in rows if course_ref in r.Subject.name or r.Subject.name in course_ref
        ]
        if not matched:
            return False, f"没找到你教的课程“{course_ref}”", {}
        if len(matched) > 1:
            names = "、".join(r.Subject.name for r in matched)
            return False, f"课程“{course_ref}”匹配到多个（{names}），请补充更完整课程名", {}
        schedule, subject = matched[0]
        enrolled = (await db.execute(
            select(CourseSelection).where(
                CourseSelection.student_id == student.id,
                CourseSelection.schedule_id == schedule.id,
                CourseSelection.status == 1,
            )
        )).scalar_one_or_none()
        if not enrolled:
            return False, f"学生 {student.id} 未选该课程", {}
        score_type = (params.get("score_type") or "期末").strip()
        if score_type not in ("平时", "期末"):
            return False, "成绩类型只能是“平时”或“期末”", {}
        return True, "", {
            "schedule_id": schedule.id,
            "student_id": student.id,
            "student_name": student.name,
            "course": subject.name,
            "score": score,
            "score_type": score_type,
        }
```

`execute_confirm` 内（在 `action == "leave_apply"` 分支之后）新增：

```python
        if action == "score_entry":
            ok, reason, info = await self._precheck_score_entry(payload, payload["user_id"], db)
            if not ok:
                return [AgentMessage(kind="error", title="业务失败", content=reason, data=info)]
            try:
                from app.services.score_service import record_score

                inserted, updated = await record_score(
                    db, schedule_id=info["schedule_id"], student_id=info["student_id"],
                    score=info["score"], score_type=info["score_type"],
                )
                await db.commit()
            except Exception:
                await db.rollback()
                logger.exception("agent score entry failed")
                return [AgentMessage(kind="error", title="系统异常", content="成绩录入失败，请稍后重试")]
            verb = "更新" if updated else "录入"
            self.sessions.add_fact(
                user_id, session_id,
                f"已{verb}成绩：{info['student_name']} {info['course']} {info['score']}分（{info['score_type']}）",
            )
            return [AgentMessage(
                kind="card", title="成绩录入成功",
                content=f"已{verb} {info['student_name']} 的 {info['course']}：{info['score']} 分（{info['score_type']}）",
                data=info,
            )]
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent_actions.py tests/test_agent_api.py -q`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add app/services/agent/actions.py tests/test_agent_actions.py tests/test_agent_api.py
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "feat(agent): teacher score entry with confirmation"
```

---

## Task 6: 前端教师快捷提示

**Files:**
- Modify: `student-management-frontend/src/views/Agent.vue`

- [ ] **Step 1: 修改**

`Agent.vue` script 区（`import AgentLogo from '../components/AgentLogo.vue'` 之后）新增：

```js
import { useAuthStore } from '../stores/auth'
```

`const store = useAgentStore()` 之后新增：

```js
const auth = useAuthStore()
```

`const quickPrompts = [...]` 行替换为：

```js
const quickPrompts = computed(() =>
  auth.role === 'teacher'
    ? ['把张三的高数成绩录成90分', '查一下2024级计算机科学1班的课表', '查一下5班有哪些学生', '查我的监考安排']
    : ['明天上什么课', '给明天学习方案', '帮我选人工智能实战', '打开选课页面']
)
```

（`computed` 已在文件顶部导入；`useAuthStore` 的 `role` 字段来自 `stores/auth.js`，路由守卫已使用。）

- [ ] **Step 2: 构建验证**

Run: `cd student-management-frontend; npm run build`
Expected: 构建成功，无报错

- [ ] **Step 3: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add student-management-frontend/src/views/Agent.vue
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "feat(frontend): teacher quick prompts on agent page"
```

---

## Task 7: README 指令表同步

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 修改**

在“智能体助手”的“已支持指令”表格中追加教师示例行：

```markdown
| 查班级课表 | “查一下2024级计算机科学1班的课表” |
| 查学生名单 | “查一下5班有哪些学生” |
| 录入成绩 | “把张三的高数成绩录成90分”（写操作，需教师确认） |
| 查我的监考 | “查我的监考安排” |
```

- [ ] **Step 2: 自查**

Run: `git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" diff -- README.md`
Expected: 仅新增上述 4 行

- [ ] **Step 3: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add README.md
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "docs: teacher agent commands in README"
```

---

## 全量验证

- [ ] 运行 `.venv\Scripts\python.exe -m pytest -q`，全部通过（原 108 + 新增用例）
- [ ] `cd student-management-frontend; npm run build` 成功
- [ ] 用 T10001 / test123456 登录，实测：查班级课表、查学生名单、查我的监考、录入成绩（确认后落库并出总评）

## 自检记录

**Spec 覆盖：** 3 个新意图 → Task 1/2/3/5；监考复用 → Task 1（提示词/规则词）+ Task 7（README）；权限矩阵 → Task 2；成绩录入确认流 → Task 5；score_service 复用 → Task 4；角色感知提示词 → Task 1；教师快捷提示 → Task 6；测试 → 各任务 TDD + 全量验证；README → Task 7。

**无占位符：** 每个代码步骤均含完整代码与预期输出。

**类型一致性：** `record_score(db, schedule_id=..., student_id=..., score=..., score_type=...)` 在 Task 4 定义、Task 5 调用，签名一致；`_precheck_score_entry(params, user_id, db)` 在 handler 与 `execute_confirm` 中调用一致；`_resolve_class(class_ref, db)` 返回 `(obj|None, err|None)`，Task 2/3 使用一致。

**已知边界：** 教师说“查课表”且 LLM 不可用时规则会落到 `query_schedule` 并被权限拦截（提示词已引导 LLM 识别为 `query_class_schedule`）；这是可接受的降级行为。
