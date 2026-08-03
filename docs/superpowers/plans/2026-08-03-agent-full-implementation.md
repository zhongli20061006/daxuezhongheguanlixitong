# 智伴校园智能体全量实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地统一系统提示词（BASE + 三任务层），并补齐成绩查询、通知查看、请假审批、考试查询四个新智能体功能。

**Architecture:** 提示词管行为（身份/铁律/格式/示例，集中在 `app/services/agent/prompts.py`），代码管确定性（日期/课程解析、确认令牌、规则兜底不动）。新功能复用既有"意图参数抽取 → 预检 → 确认卡片 → 确认执行"模式：只读功能直接返回卡片，审批走二次确认。

**Tech Stack:** FastAPI + SQLAlchemy async + Vue 3 + pytest（sqlite 内存测试库）。

**Spec:** `docs/superpowers/specs/2026-08-03-agent-system-prompt-design.md`

**当前工作区状态：** 工作区已有一份未提交的草稿 `app/services/agent/prompts.py` 和 `app/services/agent/intent.py` 改动（讨论前产物）。Task 1/2 会以本计划中的完整代码覆盖它们，无需先清理。

---

### Task 1: 统一系统提示词模块

**Files:**
- Create: `app/services/agent/prompts.py`（覆盖现有草稿）
- Test: `tests/test_agent_intent.py`（追加常量断言用例）

- [ ] **Step 1: 写失败测试（常量存在且包含铁律）**

在 `tests/test_agent_intent.py` 顶部导入后追加：

```python
from app.services.agent.prompts import (
    BASE_SYSTEM_PROMPT, CHAT_SYSTEM_PROMPT, INTENT_SYSTEM_PROMPT, PLAN_SYSTEM_PROMPT,
)


def test_unified_prompts_contain_identity_and_rules():
    assert "智伴校园" in BASE_SYSTEM_PROMPT
    assert "绝不声称" in BASE_SYSTEM_PROMPT
    assert "确认" in CHAT_SYSTEM_PROMPT
    assert "意图解析员" in INTENT_SYSTEM_PROMPT
    assert "学习规划师" in PLAN_SYSTEM_PROMPT
    assert "approve_leave" in INTENT_SYSTEM_PROMPT
    assert "query_scores" in INTENT_SYSTEM_PROMPT
    assert "query_exams" in INTENT_SYSTEM_PROMPT
    assert "query_notifications" in INTENT_SYSTEM_PROMPT
```

- [ ] **Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_agent_intent.py::test_unified_prompts_contain_identity_and_rules -q`
Expected: FAIL（当前草稿 prompt 缺新意图文案，或导入路径不符）

- [ ] **Step 3: 实现完整 `app/services/agent/prompts.py`**

```python
"""智能体统一系统提示词：角色、边界、输出规范集中维护。

定位：提示词管"模型的嘴和规矩"（身份 / 边界 / 格式 / 示例），
确定性的解析与执行（日期、课程匹配、确认令牌、规则兜底）仍由代码负责。
新增功能时优先在这里补充说明，避免按功能零散打补丁。
"""

BASE_SYSTEM_PROMPT = (
    "你是“智伴校园”平台的 AI 智能体助手，帮助学生、教师、后勤完成校园事务："
    "选课、退课、查课表、学习方案、请假、教室预约、报修、审批、查成绩、查通知、查考试等，也可以闲聊。\n"
    "铁律：\n"
    "1. 你只负责理解意图、回答问题、生成方案；写操作由系统执行，未经系统返回成功结果，"
    "绝不声称“已提交/已选课/已请假/已预约”。\n"
    "2. 写操作需要用户二次确认，你负责引导用户走确认流程，不要代替用户确认。\n"
    "3. 课程名、日期等具体信息以用户原话为准，可保留简称（如“摄影课”），"
    "不要编造完整名称或日期。\n"
    "4. 不确定、做不到时如实说明，绝不编造。\n"
    "5. 用简洁的中文回答。"
)

INTENT_TASK_PROMPT = (
    "你是一个意图解析员，只输出意图解析 JSON。\n"
    "可选意图：\n"
    "- navigate：仅当用户明确要求打开/跳转页面，params.page 必须是已知页面路径"
    "（如 /schedule、/selection、/classrooms、/repairs、/leaves）\n"
    "- query_schedule：查课表；study_plan：学习方案；query_classroom：查空教室\n"
    "- query_scores：查成绩/绩点 params.student（学号，不填表示查自己）\n"
    "- query_notifications：查通知/未读数\n"
    "- query_exams：查考试安排/监考安排\n"
    "- enroll：选课 params.course；drop：退课 params.course"
    "（course 保留用户原话，可为简称如“摄影课”，系统会自动模糊匹配）\n"
    "- reserve_classroom：预约教室 params.classroom/week/day_of_week/period/reason"
    "（week 1-52，day_of_week 1-7，period 如“1-2”，reason 预约理由）\n"
    "- repair_submit：报修 params.location/type/description"
    "（type 只能取：水电设备/电子产品/家具类/教学用具）\n"
    "- leave_apply：请假 params.start_date/end_date/reason"
    "（日期转成 YYYY-MM-DD 实际日期，“明天”写明天日期；没说结束日期只给 start_date）\n"
    "- approve_leave：审批请假 params.leave（请假编号或学生姓名/学号）/result"
    "（通过/驳回）/comment（意见，可选）\n"
    "- chat：仅当与上述动作无关时才用\n"
    "规则：用户说“请假/报修/预约/选课/退课/审批”等，即使带“帮我直接提交”，"
    "也必须返回对应写操作意图；参数缺失也要返回该意图（params 可为空），"
    "不要返回 chat，不要代写文案。\n"
    "示例1：用户说“帮我选摄影课”→"
    '{"intents":[{"intent":"enroll","params":{"course":"摄影课"},"confidence":0.9}]}\n'
    "示例2：用户说“请假：帮我直接提交”→"
    '{"intents":[{"intent":"leave_apply","params":{},"confidence":0.9}]}\n'
    "示例3：用户说“审批3号请假，通过”→"
    '{"intents":[{"intent":"approve_leave","params":{"leave":"3","result":"通过"},"confidence":0.9}]}\n'
    '输出格式：{"intents":[{"intent":"...","params":{...},"confidence":0.9}]}'
)

INTENT_SYSTEM_PROMPT = BASE_SYSTEM_PROMPT + "\n\n" + INTENT_TASK_PROMPT

CHAT_SYSTEM_PROMPT = BASE_SYSTEM_PROMPT + (
    "\n\n你是一个校园对话助手，根据对话事实返回自然语言。\n"
    "【写操作铁律】禁止在用户完成确认前，以任何文字形式表示操作已执行"
    "（如“已提交/已选课/请等待审批”）。写操作只能通过系统生成的确认卡片完成；"
    "你的职责是引导用户点击“确认执行”或回复“确认”，并如实说明当前还没有执行成功的结果。\n"
    "示例：用户问“提交成功了吗”且系统未返回成功 → 回答“还没有执行，需要你点击确认卡片完成提交”。"
)

PLAN_SYSTEM_PROMPT = BASE_SYSTEM_PROMPT + (
    "\n\n你是一个学习规划师，根据课表数据输出结构化方案 JSON。\n"
    '输出格式：{"courses":[{"course":"课程名","duration_minutes":60,"preview":"预习要点",'
    '"review":"复习要点","priority":"高/中/低"}],"summary":"一句话整体安排"}。'
    "只输出 JSON，不要多余文字。\n"
    "示例：课表“1. 高等数学 08:00-10:00 教一楼；2. 大学英语 14:00-16:00 教三楼”→"
    '{"courses":[{"course":"高等数学","duration_minutes":120,"preview":"预习导数概念",'
    '"review":"复习极限与连续","priority":"高"},{"course":"大学英语","duration_minutes":120,'
    '"preview":"预习课文生词","review":"整理语法笔记","priority":"中"}],'
    '"summary":"上午高数下午英语，晚上完成作业并回顾要点"}'
)
```

- [ ] **Step 4: 运行确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_agent_intent.py::test_unified_prompts_contain_identity_and_rules -q`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add app/services/agent/prompts.py tests/test_agent_intent.py
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "feat(agent): unified system prompts module"
```

---

### Task 2: 意图层接入新提示词与四个新意图

**Files:**
- Modify: `app/services/agent/intent.py`
- Test: `tests/test_agent_intent.py`

- [ ] **Step 1: 写失败测试（新意图的规则识别与参数抽取）**

在 `tests/test_agent_intent.py` 追加：

```python
def test_rules_query_scores():
    intent = match_rules("查一下我的成绩")
    assert intent.intent == IntentType.query_scores
    assert intent.need_confirm is False


def test_rules_query_notifications():
    intent = match_rules("查看我的通知")
    assert intent.intent == IntentType.query_notifications


def test_rules_query_exams():
    intent = match_rules("我的考试安排")
    assert intent.intent == IntentType.query_exams


def test_rules_approve_leave_extracts_params():
    intent = match_rules("审批3号请假，通过")
    assert intent.intent == IntentType.approve_leave
    assert intent.need_confirm is True
    assert intent.params["leave"] == "3"
    assert intent.params["result"] == "通过"


def test_rules_approve_reject():
    intent = match_rules("驳回1号请假")
    assert intent.intent == IntentType.approve_leave
    assert intent.params["result"] == "驳回"
```

- [ ] **Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_agent_intent.py -q`
Expected: 新增用例 FAIL

- [ ] **Step 3: 实现 `intent.py` 改动**

3a. `IntentType` 枚举追加四个值（放在 `leave_apply` 之后、`chat` 之前）：

```python
    approve_leave = "approve_leave"
    query_scores = "query_scores"
    query_notifications = "query_notifications"
    query_exams = "query_exams"
```

3b. `WRITE_INTENTS` 追加 `IntentType.approve_leave`。

3c. `RULE_TABLE` 在 `(IntentType.query_classroom, ...)` 行之后插入三行（`query_exams` 放 `query_scores` 之前，避免"考试成绩"被成绩规则抢先）：

```python
    (IntentType.query_exams, ["考试", "监考"], None),
    (IntentType.query_scores, ["成绩", "绩点"], None),
    (IntentType.query_notifications, ["通知", "未读"], None),
```

并在 `(IntentType.leave_apply, ...)` 行**之前**插入（必须在前，否则"审批3号请假"会被 leave_apply 的"请假"关键词抢先）：

```python
    (IntentType.approve_leave, ["审批", "批准", "驳回", "同意请假"], None),
```

3d. 新增审批参数抽取函数（放在 `_extract_reserve_params` 之后）：

```python
def _extract_approve_params(text: str) -> dict[str, str]:
    """规则兜底：抽取审批的请假编号/学生、结果与意见。"""
    params: dict[str, str] = {}
    if "驳回" in text:
        params["result"] = "驳回"
    elif any(k in text for k in ("通过", "同意", "批准")):
        params["result"] = "通过"
    m = re.search(r"(?:第)?\s*(\d+)\s*(?:号|条)", text)
    if m:
        params["leave"] = m.group(1)
    m = re.search(r"([\u4e00-\u9fa5]{2,4})(?:同学)?的请假", text)
    if m:
        params["student"] = m.group(1)
    m = re.search(r"(?:意见|备注)[:：]?\s*([^，。,.！!？?\s]{1,30})", text)
    if m:
        params["comment"] = m.group(1).strip()
    return params
```

3e. `extract_params_for` 增加分支：

```python
    if intent_type == IntentType.approve_leave:
        return _extract_approve_params(text)
```

3f. `match_rules` 内部分发增加分支（放在 reserve_classroom 分支之后）：

```python
                elif intent == IntentType.approve_leave:
                    params = _extract_approve_params(lowered)
```

3g. 确认 `from app.services.agent.prompts import INTENT_SYSTEM_PROMPT` 已在文件顶部（Task 1 已完成接入；若草稿中仍是 `EXTRACT_SYSTEM_PROMPT`，删除旧常量定义并统一替换为 `INTENT_SYSTEM_PROMPT`）。

- [ ] **Step 4: 运行确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_agent_intent.py -q`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add app/services/agent/intent.py tests/test_agent_intent.py
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "feat(agent): add scores/notifications/approval/exam intents"
```

---

### Task 3: 聊天与学习方案接入统一提示词

**Files:**
- Modify: `app/services/agent/actions.py`
- Test: `tests/test_agent_actions.py`

- [ ] **Step 1: 写失败测试（聊天首条消息为系统提示词）**

在 `tests/test_agent_actions.py` 的 `FakeLLM` 类之后追加：

```python
class CapturingLLM(FakeLLM):
    def __init__(self):
        super().__init__()
        self.captured = None

    async def chat(self, messages):
        self.captured = messages
        return "模型回复"
```

并在文件末尾追加：

```python
@pytest.mark.asyncio
async def test_chat_prepends_system_prompt(db):
    llm = CapturingLLM()
    executor = ActionExecutor(llm, ConfirmationStore(), SessionStore())
    await executor.execute(
        Intent(intent=IntentType.chat), "S2024001", "student", "s1", db, raw_text="你好"
    )
    assert llm.captured[0]["role"] == "system"
    assert "智伴校园" in llm.captured[0]["content"]
    assert "确认卡片" in llm.captured[0]["content"]
    assert llm.captured[-1] == {"role": "user", "content": "你好"}
```

- [ ] **Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_agent_actions.py::test_chat_prepends_system_prompt -q`
Expected: FAIL（首条消息不是系统提示词）

- [ ] **Step 3: 实现 `actions.py` 改动**

3a. 文件顶部导入追加：

```python
from app.services.agent.prompts import CHAT_SYSTEM_PROMPT, PLAN_SYSTEM_PROMPT
```

3b. `_handle_chat` 改为（整体替换原方法体）：

```python
    async def _handle_chat(self, user_id, session_id, raw_text):
        from app.services.agent import AgentMessage

        context = self.sessions.build_context(user_id, session_id)
        messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
        messages.extend(context)
        if not messages or messages[-1]["content"] != raw_text:
            messages.append({"role": "user", "content": raw_text or "你好"})
        reply = await self.llm.chat(messages)
        return [AgentMessage(kind="text", content=reply)]
```

3c. `_generate_plan` 中调用 `extract_json` 的 system 消息替换为：

```python
            data = await self.llm.extract_json([
                {"role": "system", "content": PLAN_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ])
```

- [ ] **Step 4: 运行确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_agent_actions.py -q`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add app/services/agent/actions.py tests/test_agent_actions.py
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "feat(agent): wire chat and plan prompts"
```

---

### Task 4: 只读新功能（成绩/通知/考试）handler

**Files:**
- Modify: `app/services/agent/actions.py`
- Test: `tests/test_agent_actions.py`

- [ ] **Step 1: 写失败测试**

`tests/test_agent_actions.py` 的模型导入追加：

```python
from app.models import (
    ApprovalConfig, ApprovalRecord, Classroom, ClassroomReservation, CourseCapacity,
    CourseSelection, Exam, ExamArrangement, ExamStudent, LeaveApplication, Notification,
    NotificationUser, Repair, Schedule, Score, ScoreType, Student, StudentClass,
    Subject, SubjectType, SystemConfig, Teacher,
)
```

文件末尾追加：

```python
@pytest.mark.asyncio
async def test_query_scores_returns_card(db, test_engine):
    await _seed(db, test_engine)
    db.add(Score(
        student_id="S2024001", schedule_id=1, score=88, gpa=3.7,
        score_type=ScoreType.daily, attempt=1,
    ))
    await db.commit()
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.query_scores), "S2024001", "student", "s1", db
    )
    assert msgs[0].kind == "card"
    assert msgs[0].data["scores"][0]["course"] == "人工智能实战"
    assert msgs[0].data["scores"][0]["score"] == 88


@pytest.mark.asyncio
async def test_query_notifications_returns_card(db, test_engine):
    await _seed(db, test_engine)
    n = Notification(title="测试通知", content="通知内容", event_type="x")
    db.add(n)
    await db.flush()
    db.add(NotificationUser(notification_id=n.id, recipient_id="S2024001", is_read=False))
    await db.commit()
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.query_notifications), "S2024001", "student", "s1", db
    )
    assert msgs[0].kind == "card"
    assert msgs[0].data["notifications"][0]["title"] == "测试通知"
    assert msgs[0].data["unread"] == 1


@pytest.mark.asyncio
async def test_query_exams_student_returns_card(db, test_engine):
    await _seed(db, test_engine)
    db.add(Exam(
        id=1, semester="2024-2025-1", subject_id=2, schedule_id=1,
        exam_type="统一考试", duration_minutes=120, status="已发布",
    ))
    await db.flush()
    db.add(ExamArrangement(
        exam_id=1, classroom_id=1, date=date(2026, 8, 10),
        start_time="09:00", end_time="11:00", invigilator_id="T10001",
    ))
    await db.flush()
    db.add(ExamStudent(exam_id=1, student_id="S2024001", seat_no=3))
    await db.commit()
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.query_exams), "S2024001", "student", "s1", db
    )
    assert msgs[0].kind == "card"
    assert msgs[0].data["exams"][0]["subject"] == "人工智能实战"
    assert msgs[0].data["exams"][0]["seat"] == 3
```

- [ ] **Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_agent_actions.py -q`
Expected: 新增 3 个用例 FAIL

- [ ] **Step 3: 实现 `actions.py` 改动**

3a. `app/models` 导入追加：

```python
    Exam, ExamArrangement, ExamStudent, Score,
```

3b. 权限集合追加（`NOT_FOR_ADMIN` 后面）：

```python
NOT_FOR_ADMIN = frozenset({
    IntentType.reserve_classroom, IntentType.repair_submit, IntentType.leave_apply,
    IntentType.query_scores, IntentType.query_exams,
})
```

3c. `_handle_query_classroom` 之后新增三个 handler：

```python
    async def _handle_query_scores(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        student_id = (intent.params.get("student") or "").strip() or user_id
        if role == "student" and student_id != user_id:
            return [AgentMessage(kind="error", title="业务失败", content="只能查看自己的成绩")]
        rows = (await db.execute(
            select(Score, Subject)
            .join(Schedule, Score.schedule_id == Schedule.id)
            .join(Subject, Schedule.subject_id == Subject.id)
            .where(Score.student_id == student_id)
            .order_by(Subject.name, Score.score_type)
        )).all()
        if not rows:
            return [AgentMessage(kind="card", title="我的成绩", content="暂无成绩记录", data={"scores": []})]
        scores = [{
            "course": subj.name, "credit": float(subj.credit),
            "score": float(sc.score) if sc.score is not None else None,
            "gpa": float(sc.gpa),
            "type": sc.score_type if isinstance(sc.score_type, str) else str(sc.score_type.value),
        } for sc, subj in rows]
        return [AgentMessage(kind="card", title="我的成绩", content=f"共 {len(scores)} 条成绩记录", data={"scores": scores})]

    async def _handle_query_notifications(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage
        from app.services.notification_service import notification_service

        items = await notification_service.get_user_notifications(db, user_id, role, limit=5, offset=0)
        unread = await notification_service.get_unread_count(db, user_id, role)
        if not items:
            return [AgentMessage(kind="card", title="通知中心", content=f"暂无通知，未读 {unread} 条",
                                 data={"notifications": [], "unread": unread})]
        return [AgentMessage(kind="card", title="通知中心", content=f"最新 {len(items)} 条，未读 {unread} 条",
                             data={"notifications": items, "unread": unread})]

    async def _handle_query_exams(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        if role == "student":
            rows = (await db.execute(
                select(Exam, Subject, ExamArrangement, Classroom, ExamStudent)
                .join(Subject, Exam.subject_id == Subject.id)
                .join(ExamArrangement, Exam.id == ExamArrangement.exam_id)
                .join(Classroom, ExamArrangement.classroom_id == Classroom.id)
                .join(ExamStudent, Exam.id == ExamStudent.exam_id)
                .where(ExamStudent.student_id == user_id)
                .order_by(ExamArrangement.date.asc(), ExamArrangement.start_time.asc())
            )).all()
            title = "我的考试"
            items = [{
                "subject": s.name, "classroom": c.name,
                "date": a.date.isoformat() if a.date else None,
                "time": f"{a.start_time}-{a.end_time}", "status": e.status, "seat": es.seat_no,
            } for e, s, a, c, es in rows]
        else:
            rows = (await db.execute(
                select(Exam, Subject, ExamArrangement, Classroom)
                .join(Subject, Exam.subject_id == Subject.id)
                .join(ExamArrangement, Exam.id == ExamArrangement.exam_id)
                .join(Classroom, ExamArrangement.classroom_id == Classroom.id)
                .where(ExamArrangement.invigilator_id == user_id)
                .order_by(ExamArrangement.date.asc(), ExamArrangement.start_time.asc())
            )).all()
            title = "我的监考安排"
            items = [{
                "subject": s.name, "classroom": c.name,
                "date": a.date.isoformat() if a.date else None,
                "time": f"{a.start_time}-{a.end_time}", "status": e.status, "seat": None,
            } for e, s, a, c in rows]
        if not items:
            return [AgentMessage(kind="card", title=title, content="暂无安排", data={"exams": []})]
        return [AgentMessage(kind="card", title=title, content=f"共 {len(items)} 场", data={"exams": items})]
```

- [ ] **Step 4: 运行确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_agent_actions.py -q`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add app/services/agent/actions.py tests/test_agent_actions.py
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "feat(agent): score/notification/exam query handlers"
```

---

### Task 5: 请假审批（写操作，含二次确认）

**Files:**
- Modify: `app/services/agent/actions.py`
- Test: `tests/test_agent_actions.py`

- [ ] **Step 1: 写失败测试**

`tests/test_agent_actions.py` 追加：

```python
async def _seed_pending_leave(db, test_engine) -> int:
    await _seed(db, test_engine)
    leave = LeaveApplication(
        student_id="S2024001",
        start_date=date.today() + timedelta(days=1),
        end_date=date.today() + timedelta(days=1),
        total_days=1, reason="感冒", status="审批中(辅导员)",
    )
    db.add(leave)
    await db.commit()
    await db.refresh(leave)
    return leave.id


@pytest.mark.asyncio
async def test_approve_leave_confirmation_then_execute(db, test_engine):
    leave_id = await _seed_pending_leave(db, test_engine)
    executor = _executor()
    intent = Intent(intent=IntentType.approve_leave, params={
        "leave": str(leave_id), "result": "通过",
    }, need_confirm=True)
    msgs = await executor.execute(intent, "T10001", "teacher", "s1", db)
    assert msgs[0].kind == "confirmation"
    token = msgs[0].confirm_token
    results = await executor.execute_confirm(executor.confirmations.consume("T10001", token), db)
    assert results[0].kind == "card"
    assert "已通过" in results[0].content
    leaves = (await db.execute(select(LeaveApplication))).scalars().all()
    assert leaves[0].status == "已通过"


@pytest.mark.asyncio
async def test_approve_leave_reject(db, test_engine):
    leave_id = await _seed_pending_leave(db, test_engine)
    executor = _executor()
    intent = Intent(intent=IntentType.approve_leave, params={
        "leave": str(leave_id), "result": "驳回", "comment": "材料不全",
    }, need_confirm=True)
    msgs = await executor.execute(intent, "T10001", "teacher", "s1", db)
    token = msgs[0].confirm_token
    await executor.execute_confirm(executor.confirmations.consume("T10001", token), db)
    leaves = (await db.execute(select(LeaveApplication))).scalars().all()
    assert leaves[0].status == "已驳回"


@pytest.mark.asyncio
async def test_approve_leave_student_forbidden(db, test_engine):
    await _seed_pending_leave(db, test_engine)
    executor = _executor()
    msgs = await executor.execute(
        Intent(intent=IntentType.approve_leave, params={"leave": "1", "result": "通过"}),
        "S2024001", "student", "s1", db,
    )
    assert msgs[0].kind == "error"
```

- [ ] **Step 2: 运行确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_agent_actions.py -q`
Expected: 新增 3 个用例 FAIL

- [ ] **Step 3: 实现 `actions.py` 改动**

3a. 权限集合追加：

```python
NOT_FOR_STUDENT = frozenset({IntentType.approve_leave})
```

3b. `_allowed` 函数追加判断：

```python
    if intent in NOT_FOR_STUDENT and role == "student":
        return False
```

3c. `_handle_leave_apply` 之后新增 handler 与解析辅助：

```python
    async def _handle_approve_leave(self, intent, user_id, role, session_id, db):
        from app.services.agent import AgentMessage

        leave = await self._resolve_pending_leave(intent.params, user_id, role, db)
        if leave is None:
            return [AgentMessage(kind="error", title="业务失败",
                                 content="没找到可审批的请假，请提供请假编号或学生姓名/学号")]
        result = (intent.params.get("result") or "").strip()
        if result not in ("通过", "驳回"):
            return [AgentMessage(kind="error", title="业务失败", content="请说明审批结果：通过 或 驳回")]
        info = {
            "leave_id": leave.id, "student": leave.student_id,
            "days": leave.total_days, "reason": leave.reason, "result": result,
        }
        token = self.confirmations.create(user_id, {
            "action": "approve_leave", "leave_id": leave.id, "result": result,
            "comment": (intent.params.get("comment") or "").strip(),
            "role": role, "user_id": user_id, "session_id": session_id,
        })
        return [AgentMessage(
            kind="confirmation", title="确认审批",
            content=f"对 {leave.student_id} 的请假（{leave.total_days}天）执行「{result}」",
            data=info, confirm_token=token,
        )]

    async def _resolve_pending_leave(self, params, user_id, role, db):
        """在待审批列表中按请假编号或学生姓名/学号定位记录。"""
        from app.models import LeaveApplication, Student
        from app.services.leave_service import leave_service

        ref = (params.get("leave") or "").strip()
        if not ref:
            return None
        approver_role = "admin" if role == "admin" else "advisor"
        class_id = None
        if role == "teacher":
            t = (await db.execute(
                select(Teacher).where(Teacher.job_number == user_id)
            )).scalar_one_or_none()
            if not t:
                return None
            classes = (await db.execute(
                select(StudentClass).where(StudentClass.advisor_id == t.id)
            )).scalars().all()
            class_id = classes[0].id if classes else -1
        rows = await leave_service.get_pending_approvals(db, approver_role, class_id)
        if ref.isdigit():
            target = int(ref)
            return next((l for l, _ in rows if l.id == target), None)
        for l, s in rows:
            if ref in (l.student_id, s.name):
                return l
        return None
```

3d. `execute_confirm` 中 `reserve_classroom` 分支之后、`return [AgentMessage(kind="error", content="未知的确认动作")]` 之前新增：

```python
        if action == "approve_leave":
            from app.services.leave_service import leave_service

            approver_role = "admin" if payload.get("role") == "admin" else "advisor"
            is_college_admin = False
            if payload.get("role") == "teacher":
                t = (await db.execute(
                    select(Teacher).where(Teacher.job_number == user_id)
                )).scalar_one_or_none()
                is_college_admin = bool(t and t.is_college_admin)
            try:
                leave = await leave_service.approve(
                    db, int(payload["leave_id"]), user_id, approver_role,
                    payload["result"], payload.get("comment"),
                    is_college_admin=is_college_admin,
                )
            except ValueError as exc:
                await db.rollback()
                return [AgentMessage(kind="error", title="业务失败", content=str(exc))]
            except Exception:
                await db.rollback()
                logger.exception("agent approve leave failed")
                return [AgentMessage(kind="error", title="系统异常", content="审批失败，请稍后重试")]
            self.sessions.add_fact(user_id, session_id, f"已审批请假 #{leave.id}：{payload['result']}")
            return [AgentMessage(
                kind="card", title="审批完成",
                content=f"请假 #{leave.id} 已{payload['result']}，当前状态：{leave.status}",
                data={"leave_id": leave.id, "status": leave.status},
            )]
```

- [ ] **Step 4: 运行确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_agent_actions.py -q`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add app/services/agent/actions.py tests/test_agent_actions.py
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "feat(agent): leave approval with confirmation"
```

---

### Task 6: API 层端到端测试（四个新功能）

**Files:**
- Modify: `tests/test_agent_api.py`

- [ ] **Step 1: 写测试**

`tests/test_agent_api.py` 的模型导入追加 `Exam, ExamArrangement, ExamStudent, Notification, NotificationUser, Score, ScoreType`。文件末尾追加：

```python
@pytest.mark.asyncio
async def test_chat_query_scores(client, db, test_engine, auth_override, fake_llm):
    await _seed_agent_data(db, test_engine)
    db.add(Score(
        student_id="S2024001", schedule_id=1, score=88, gpa=3.7,
        score_type=ScoreType.daily, attempt=1,
    ))
    await db.commit()
    resp = await client.post("/agent/chat", json={"message": "查一下我的成绩"})
    assert resp.status_code == 200
    kinds = [m["kind"] for m in resp.json()["messages"]]
    assert "card" in kinds


@pytest.mark.asyncio
async def test_chat_query_notifications(client, db, test_engine, auth_override, fake_llm):
    await _seed_agent_data(db, test_engine)
    n = Notification(title="考试提醒", content="周日下午考试", event_type="exam")
    db.add(n)
    await db.flush()
    db.add(NotificationUser(notification_id=n.id, recipient_id="S2024001", is_read=False))
    await db.commit()
    resp = await client.post("/agent/chat", json={"message": "查看我的通知"})
    assert resp.status_code == 200
    assert any(m["kind"] == "card" for m in resp.json()["messages"])


@pytest.mark.asyncio
async def test_chat_query_exams(client, db, test_engine, auth_override, fake_llm):
    await _seed_agent_data(db, test_engine)
    db.add(Exam(id=1, semester="2024-2025-1", subject_id=2, schedule_id=1,
                exam_type="统一考试", duration_minutes=120, status="已发布"))
    await db.flush()
    db.add(ExamArrangement(exam_id=1, classroom_id=1, date=date(2026, 8, 10),
                           start_time="09:00", end_time="11:00", invigilator_id="T10001"))
    await db.flush()
    db.add(ExamStudent(exam_id=1, student_id="S2024001", seat_no=3))
    await db.commit()
    resp = await client.post("/agent/chat", json={"message": "我的考试安排"})
    assert resp.status_code == 200
    assert any(m["kind"] == "card" for m in resp.json()["messages"])


@pytest.mark.asyncio
async def test_chat_approve_leave_teacher_flow(client, db, test_engine, fake_llm, monkeypatch):
    """教师审批：确认卡片 → 文本确认 → 状态流转。"""
    from app.deps import get_current_user
    from app.main import app

    await _seed_agent_data(db, test_engine)
    leave = LeaveApplication(
        student_id="S2024001",
        start_date=date.today() + timedelta(days=1),
        end_date=date.today() + timedelta(days=1),
        total_days=1, reason="感冒", status="审批中(辅导员)",
    )
    db.add(leave)
    await db.commit()
    await db.refresh(leave)

    app.dependency_overrides[get_current_user] = lambda: {
        "username": "T10001", "role": "teacher", "role_id": "T10001",
    }
    try:
        resp = await client.post("/agent/chat", json={
            "message": f"审批{leave.id}号请假，通过",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "confirmation" in [m["kind"] for m in data["messages"]]
        sid = data["session_id"]

        resp2 = await client.post("/agent/chat", json={"session_id": sid, "message": "确认"})
        assert resp2.status_code == 200
        assert resp2.json()["source"] == "confirm"
        leaves = (await db.execute(select(LeaveApplication))).scalars().all()
        assert leaves[0].status == "已通过"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
```

- [ ] **Step 2: 运行确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_agent_api.py -q`
Expected: 全部 PASS（含原有用例）

- [ ] **Step 3: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add tests/test_agent_api.py
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "test(agent): api flows for new intents"
```

---

### Task 7: 前端结果卡片表格

**Files:**
- Modify: `student-management-frontend/src/views/Agent.vue`

- [ ] **Step 1: 在卡片 `el-table v-else-if="m.data?.courses"` 之后追加三个表格分支**

```html
<el-table v-else-if="m.data?.scores" :data="m.data.scores" size="small">
  <el-table-column prop="course" label="课程" />
  <el-table-column prop="score" label="分数" width="70" />
  <el-table-column prop="gpa" label="绩点" width="70" />
  <el-table-column prop="type" label="类型" width="80" />
</el-table>
<el-table v-else-if="m.data?.notifications" :data="m.data.notifications" size="small">
  <el-table-column prop="title" label="标题" />
  <el-table-column prop="content" label="内容" />
</el-table>
<el-table v-else-if="m.data?.exams" :data="m.data.exams" size="small">
  <el-table-column prop="subject" label="科目" />
  <el-table-column prop="date" label="日期" width="100" />
  <el-table-column prop="time" label="时间" width="120" />
  <el-table-column prop="classroom" label="教室" width="100" />
  <el-table-column prop="seat" label="座位" width="70" />
</el-table>
```

- [ ] **Step 2: 前端构建验证**

Run（提权）: `cd student-management-frontend; npm run build`
Expected: `✓ built`（chunk 体积警告为既有问题，非失败）

- [ ] **Step 3: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add student-management-frontend/src/views/Agent.vue
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "feat(frontend): result card tables for scores/notifications/exams"
```

---

### Task 8: README 与全量验证

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新 README 指令表与状态**

在"已支持指令"表格追加四行：

```markdown
| 查一下我的成绩 | 返回成绩与绩点卡片 |
| 查看我的通知 | 返回最新通知与未读数卡片 |
| 审批3号请假，通过 | 预检后弹出确认卡片，确认后完成审批流转 |
| 我的考试安排 | 学生返回考试安排，教师返回监考安排 |
```

并把"当前状态"段落改为：

```markdown
**当前状态**：跳转、查课表、学习方案、选课、退课、查教室、请假、报修、教室预约、查成绩、查通知、审批请假、查考试/监考已全部接入真实业务 API（写操作含预检与二次确认）。
```

- [ ] **Step 2: 全量测试 + 更新测试数**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 全部 PASS

把 README"自动化测试"一节的 `# 当前 91 passed` 改为实际数字（预计 100+）。

- [ ] **Step 3: 提交并推送**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add README.md
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "docs: agent feature list and test count"
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" push origin feat/docker-enhancement
```

Expected: push 输出含 `feat/docker-enhancement -> feat/docker-enhancement`，随后 `git status -sb` 无 ahead 标记。

---

## Self-Review（编写时已执行）

1. **Spec 覆盖**：spec 的统一提示词（Task 1/2/3）、四个新意图（Task 2 规则、Task 4 只读、Task 5 审批、Task 6 API、Task 7 前端、Task 8 文档）均有对应任务；"代码管确定性"（日期/课程解析、确认令牌、pending 续跑）不改动，符合非目标。
2. **占位符扫描**：所有代码步骤均含完整实现，无 TBD/TODO。
3. **类型一致性**：`_resolve_pending_leave` 返回 `LeaveApplication | None`；`execute_confirm` 的 `approve_leave` 分支使用 `payload["leave_id"]`、`payload["result"]`，与 handler 创建 token 时的键一致；`data` 字段名（scores/notifications/exams）与前端表格分支一致。
