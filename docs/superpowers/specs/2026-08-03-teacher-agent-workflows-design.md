# 教师端 Agent 工作流 · 设计稿

日期：2026-08-03
状态：已确认（用户已审阅对话版设计并批准）
范围：教师端 Agent 第一版

## 目标

让教师通过自然语言完成 4 个核心工作流：

1. 查班级课表（`query_class_schedule`）
2. 查学生名单（`query_students`）
3. 查我的监考（复用 `query_exams`，已按角色返回）
4. 成绩录入（`score_entry`，写操作走确认流）

配套：角色感知提示词、教师角色测试、README 指令表同步。

## 非目标

- 请假批量审批、辅导员毕业审核（另立任务）
- admin 成绩录入（与前端 `/scores/input` 的 teacher 限制一致）
- UI 重设计（Agent.vue 仅加教师快捷提示）
- staff 通过 Agent 审批请假的问题（权限风险项，另立任务收紧）

## 现状与架构映射

现有 Agent 骨架无需改动分层：

- `app/services/agent/intent.py`：意图解析（LLM + 规则兜底 + 短 TTL 缓存）
- `app/services/agent/actions.py`：`ActionExecutor`，每个意图一个 handler；`_allowed` 权限矩阵
- `app/services/agent/confirmations.py`：写操作一次性确认令牌
- `app/services/agent/prompts.py`：统一系统提示词
- `app/services/agent/session.py`：会话与待补参数（fragment 收集）

现有可复用能力：

- `query_exams` 已按角色分叉（学生→我的考试，教师→我的监考安排），无需新意图
- `approve_leave` 已演示教师写操作 + 确认流模式
- fragment 参数收集已支持"一句话给全"或"多轮追问"

## 意图设计

新增 3 个意图（`IntentType` 枚举）：

| 意图 | 参数 | 说明 |
| --- | --- | --- |
| `query_class_schedule` | `class` | 班级名，支持简称模糊匹配 |
| `query_students` | `class` / `name` / `student_id` | 三选一 |
| `score_entry` | `student` / `course` / `score` / `score_type` | `score_type` 默认"期末"，可填"平时" |

规则表补充关键词：

- `query_class_schedule`：["班级课表", "班的课表", "查课表"]
- `query_students`：["学生名单", "名单", "有哪些学生", "查学生"]
- `score_entry`：["录成绩", "录入成绩", "成绩录", "打分"]

## 权限规则

`_allowed` 变更：

- `query_class_schedule`、`query_students`、`score_entry` 加入 `NOT_FOR_STUDENT`
- `score_entry` 执行时额外校验 `role == "teacher"`（admin 不开放成绩录入）

最终防线是执行层 `_allowed`；提示词仅降低误判概率。

## 动作处理器设计

### `_handle_query_class_schedule`

1. 班级名 → `StudentClass`（name 精确/模糊匹配，取唯一命中）
2. `Schedule` JOIN `Subject`/`Teacher`/`Classroom` WHERE `class_id`
3. 按周一~周日分组输出卡片（复用学生课表卡片字段：课程、教师、教室、节次、周次）
4. 查无班级 / 多个同名班级 → 返回错误消息并请用户确认

### `_handle_query_students`

1. 按 `class` / `name` / `student_id` 查询 `Student`
2. 名单卡片字段：学号、姓名、班级
3. 按班级查询时按学号排序；结果过多时截断并提示

### `_handle_score_entry`

1. 参数收集：复用 fragment 机制；缺少 `student`/`course`/`score` 时记入 pending 并追问
2. 预检查：
   - `score` 数值且在 0-100
   - `student` 解析到唯一学生（姓名/学号）
   - `course` 解析到唯一 `Schedule`，且 `Schedule.teacher_id` 等于当前教师（工号 → teacher.id）
   - 该学生在对应 `Schedule` 的 `course_selection` 中且 `status == 1`
3. 通过后创建确认令牌：`{"action": "score_entry", "schedule_id", "student_id", "score", "score_type", "user_id", "session_id"}`
4. 返回 `confirmation` 卡片（学生、课程、分数、类型）
5. `execute_confirm` 中重新执行预检查（防止确认期间状态变化），再落库

## 成绩写入复用（小重构）

现状：录入与总评自动计算逻辑在 `app/api/score.py`（`manual_score` / `_auto_calculate_total_if_ready`）。

方案：抽到 `app/services/score_service.py`：

- `record_score(db, teacher_id, schedule_id, student_id, score, score_type) -> (inserted, updated)`
- `auto_calculate_total_if_ready(db, schedule_id) -> int`

`api/score.py` 改为调用 service，Agent 的 `execute_confirm` 同样调用，避免两套逻辑漂移。

备选：Agent 内联复制逻辑（约 40 行重复）。不采用。

## 提示词改动

`app/services/agent/prompts.py`：

- `INTENT_TASK_PROMPT` 增加 3 个新意图的说明与参数格式
- 增加教师场景示例（"查一下2024级计算机科学1班的课表"、"把张三的高数成绩录成90"、"帮我查一下5班有哪些学生"）

`app/services/agent/intent.py`：

- `resolve(text)` → `resolve(text, role)`，按角色注入可用意图段
- 缓存 key 改为 `(role, text)`

`_allowed` 仍是硬边界，提示词内容不承担权限职责。

## 前端改动（Agent.vue）

- 教师角色显示教师快捷提示：录成绩 / 查班级课表 / 查学生名单 / 我的监考
- 学生及其他角色保持现状

预计改动十几行。

## 测试计划

新增/扩展测试文件：

- `test_agent_intent.py`：3 个新意图规则匹配 + 参数抽取（含角色参数传递）
- `test_agent_actions.py`：
  - 教师各 handler 正常路径（班级课表、学生名单、成绩录入确认卡）
  - 缺参 → 追问消息
  - 越权：学生请求 `score_entry` → 无权限；教师请求 `enroll` → 无权限
  - 成绩录入确认后落库，`score` 表与总评可查
- `test_agent_api.py`：`score_entry` 确认流端到端（fake LLM + 确认 token）

回归：现有 108 个测试保持全绿。

## 涉及文件

- `app/services/agent/intent.py`
- `app/services/agent/actions.py`
- `app/services/agent/prompts.py`
- `app/api/agent.py`（`resolve` 调用点传入 role）
- `app/services/score_service.py`（新增）
- `app/api/score.py`（改调 service）
- `student-management-frontend/src/views/Agent.vue`
- `tests/test_agent_intent.py`、`tests/test_agent_actions.py`、`tests/test_agent_api.py`
- `README.md`（教师指令示例）

## 交付验证

1. `pytest` 全量通过
2. 用 T10001 / test123456 登录实测 4 个工作流（含成绩录入确认→落库→总评）
3. 前端教师角色快捷提示可见

## 风险与未验证项

- 班级名/课程名模糊匹配存在多义场景：采取"唯一命中才执行，多个命中让用户确认"策略
- 成绩录入并发（同一学生同一课程同时录入）：与 API 现有一致，接受现状
- staff 审批请假权限问题：本版不动，另立任务
