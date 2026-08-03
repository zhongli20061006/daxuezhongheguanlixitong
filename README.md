# 大学生管理系统

FastAPI + Vue 3 全栈学生管理系统，涵盖选课、成绩、课表、请假、毕业审核、报修、通知等功能。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI 0.136 + Python 3.13 |
| ORM | SQLAlchemy 2.0 (async) |
| 数据库 | MySQL 8.x |
| 前端框架 | Vue 3 (Composition API) |
| UI 组件 | Element Plus |
| 状态管理 | Pinia |
| 构建工具 | Vite 5 |

## 项目结构

```
├── app/                    # FastAPI 应用
│   ├── api/                # API 路由 (14 个)
│   ├── models/             # SQLAlchemy (20 张表)
│   ├── schemas/            # Pydantic 模型 (10 个)
│   ├── services/           # 业务逻辑层 (6 个)
│   │   └── agent/          # 智能体：意图识别 / 动作执行 / 会话记忆 / LLM 客户端
│   ├── utils/              # 工具 (绩点/周次/节次)
│   ├── config.py           # 配置
│   ├── database.py         # 数据库引擎 (async+sync)
│   ├── deps.py             # JWT 依赖注入
│   └── main.py             # 入口 (含 WS + 事件总线)
├── student-management-frontend/  # Vue 3 前端
│   └── src/
│   ├── api/            # Axios (10 个)
│   ├── views/          # 页面 (15 个)
│       ├── components/     # 组件 (3 个)
│       ├── stores/         # Pinia (3 个)
│       ├── router/         # 路由 + 导航守卫
│       └── utils/          # 工具 (4 个)
├── requirements.txt        # Python 依赖
├── init.sql                # 基础建表
├── migration_phase3.sql    # Phase 3 迁移
└── run.py                  # PyCharm 调试启动
```

## Docker 部署（推荐）

### 1. 启动所有服务

```bash
docker compose up -d
```

首次构建需 3-5 分钟（安装 Python/Node 依赖）。

### 2. 初始化种子数据

```bash
# Windows PowerShell
.\docker-init.ps1

# Linux / macOS
bash docker-init.sh
```

### 3. 访问系统

| 入口 | 地址 |
|------|------|
| 前端 | http://localhost |
| API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |

### 4. 测试账号

密码统一为 `test123456`：
- 管理员: `admin01`
- 教师: `T10001`
- 学生: `S2024001`
- 后勤: `G10001`

---

## 本地开发（手动启动）

### 1. 创建数据库

```sql
CREATE DATABASE student_management DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 配置环境

复制 `.env.example` → `.env`，修改数据库连接：
```
DATABASE_URL=mysql+aiomysql://root:密码@localhost:3306/student_management
SYNC_DATABASE_URL=mysql+pymysql://root:密码@localhost:3306/student_management
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
cd student-management-frontend && npm install
```

### 4. 建表 + 测试数据

```bash
python -m app.init_data  # 建表 + 插入测试数据 + 打印随机密码
```

### 5. 启动

```bash
# 后端 (端口 8000)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 前端 (端口 5175)
cd student-management-frontend && npm run dev
```

### 6. PyCharm 调试

右键 `run.py` → Debug 'run'

## 测试账号

所有密码统一为 `test123456`（已通过修改密码接口统一设置，原始随机密码已失效）：

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin01 | test123456 |
| 教师 | T10001 | test123456 |
| 学生 | S2024001 | test123456 |
| 后勤 | G10001 | test123456 |
| 智能体测试学生 | agent01 | test123456 |

如需使用其他 25 个测试账号，运行 `python -m app.init_data` 重新初始化。

> `agent01` 的学生 ID 也是 `agent01`（与系统"用户名=学号"约定一致），登录后个人中心、选课、智能体等功能均可用。

## 智能体助手（AI Agent）

首页即智能体对话窗口：用自然语言下达指令，系统自动识别意图并执行，不用手动点页面。

**已支持指令**

| 指令示例 | 行为 |
|----------|------|
| 打开选课页面 / 查看课表 | 自动跳转对应页面 |
| 明天上什么课 | 返回明天的课表卡片 |
| 给我明天学习方案 | 生成每门课的课前预习 / 课后复习 / 优先级方案 |
| 帮我选人工智能实战 | 预检通过后弹出确认卡片，二次确认后才真正选课 |
| 退掉人工智能实战 | 同样需要二次确认 |
| 查一下空教室 | 跳转教室查询页面 |
| 帮我预约教室D101，第3周周五1-2节 | 预检（课程占用/重复预约）后弹出确认卡片，确认后写入预约 |
| 我要报修，地点D101，投影仪坏了 | 填写地点/类型/描述，二次确认后生成报修单 |
| 我要请假 2026-08-05 到 2026-08-06 因为感冒 | 校验日期后二次确认，提交后进入辅导员/学院审批流 |

**架构**

- 意图识别与对话/学习方案生成由本地 **Ollama + Qwen2.5:7b** 完成（不接云端 API）
- **规则引擎兜底**：模型超时 / 熔断时自动降级为关键词匹配，只读操作仍可用
- **写操作一律二次确认**：确认令牌 5 分钟有效；可点击卡片"确认执行"，也可在对话里直接回复"确认"/"取消"
- **多会话管理**：每用户上限 20 个会话；上下文按 8000 token 预算裁剪，动作事实记忆（如"已选课：xx"）
- 一条消息可包含多个指令，按序执行；业务失败（如人数已满）不中断后续只读指令，系统异常才停止

**Agent API**

| 接口 | 说明 |
|------|------|
| POST /agent/chat | 发送消息（返回意图来源 llm / rules / fallback） |
| POST /agent/confirm | 确认写操作（选课 / 退课 / 请假 / 报修 / 教室预约） |
| GET /agent/status | Ollama 在线状态 + 熔断状态 |
| GET /agent/sessions | 会话列表 |
| GET / DELETE /agent/sessions/{id} | 会话历史 / 删除会话 |

**当前状态**：跳转、查课表、学习方案、选课、退课、查教室、**请假、报修、教室预约** 已全部接入真实业务 API（含预检与二次确认）。

## 本地 Ollama 部署（智能体依赖）

智能体需要本地大模型，一次部署长期使用：

1. 安装 Ollama（可静默安装到 `E:\ollama\app`）
2. 模型目录指向 E 盘，避免占用 C 盘：
   ```powershell
   [Environment]::SetEnvironmentVariable('OLLAMA_MODELS','E:\ollama\models','User')
   ```
3. 启动服务：
   ```powershell
   E:\ollama\app\ollama.exe serve
   ```
4. 拉取模型（国内走 ModelScope 源；官方仓库只有 safetensors，Ollama 需要 GGUF 仓库）：
   ```powershell
   E:\ollama\app\ollama.exe pull modelscope.cn/qwen/Qwen2.5-7B-Instruct-GGUF
   E:\ollama\app\ollama.exe cp modelscope.cn/qwen/Qwen2.5-7B-Instruct-GGUF:latest qwen2.5:7b
   ```
5. 验证：`http://localhost:11434` 可访问；`.env` 中 `OLLAMA_MODEL=qwen2.5:7b`

> 模型约 4.7GB；本机 RTX 5060 Laptop 8GB 显存可 GPU 加速。Ollama 未启动时智能体会自动降级为规则兜底（读操作仍可用，学习方案返回模板）。

## 功能模块

| 模块 | 接口 | 状态 |
|------|------|------|
| 智能体 | /agent/chat, /agent/confirm, /agent/status, /agent/sessions | ✅ |
| 认证 | /auth/login, /auth/change-password | ✅ |
| 选课 | /selection/enroll, /selection/drop, /selection/my-courses, /selection/available-courses | ✅ |
| 课表 | /schedule/my, /schedule/class/{id} + CRUD | ✅ |
| 成绩 | /scores/manual, /scores/import, /scores/calculate-total, /scores/student/{id} | ✅ |
| 请假 | /leave/apply, /leave/my, /leave/{id}/cancel, /leave/{id}/detail | ✅ |
| 审批 | /advisor/pending-approvals, /advisor/approve | ✅ |
| 教室 | /classrooms/available, /classrooms/{id}/availability, /classrooms/reserve, /classrooms/my-reservations, /classrooms/reservation/{id}/cancel | ✅ |
| 报修 | /repairs (CRUD + 状态流转) | ✅ |
| 通知 | /notification/list, /notification/unread-count, /notification/{id}/read | ✅ |
| 培养方案 | /training-plan/plans + /training-plan/courses | ✅ |
| 毕业审核 | /graduation/audit/{id}, /graduation/audit-batch, /graduation/audits | ✅ |
| 考试 | /exam/generate, /exam/list, /exam/{id}/publish, /exam/my-exams, /exam/my-invigilations | ✅ |
| 管理 | /admin/users, /admin/selection-window, /admin/capacity/{id}, /admin/reset-password | ✅ |
| 系统 | /internal/summary, /health, WS /ws | ✅ |

## E2E 全流程测试结果

```
========================================
  Results: 28 passed, 0 failed
========================================
```

测试覆盖：登录(4角色) → 个人中心 → 选课 → 退课 → 课表 → 教室(预约/取消) → 报修 → 请假(审批) → 成绩 → 通知 → 培养方案 → 毕业审核 → 考试(排考/发布/学生查看/教师监考) → 管理

## 自动化测试

```bash
python -m pytest -q    # 当前 73 passed
```

覆盖：认证、选课、课表、成绩、请假、审批、教室、报修、通知、培养方案、毕业审核、考试、管理，以及智能体模块（意图识别 / 动作执行 / 会话记忆 / 二次确认 / 种子数据 / 多意图降级等）。

## 压力测试

6 个场景并发模拟（50 学生并发选课、20 教师并发预约教室、5 教师并发审批请假等）：

| 场景 | 结果 | 说明 |
|------|------|------|
| 选课 CAS 原子操作 | ✅ | 50 人抢 50 名额，无超售 |
| 教室预约 TOCTOU | ✅ 修复后通过 | 初版 SELECT-then-INSERT 存在竞态，加 UNIQUE INDEX 后通过 |
| 请假审批非幂等 | ✅ 修复后通过 | 初版可重复审批，加审批记录 UNIQUE(leave_id, level) 后通过 |
| 考试生成 + 毕业审核 | ✅ | 批量操作正常 |
| 全部 API 健康检查 | ✅ | 8 个核心端点全部 200 |

详细记录见 [DEBUG_LOG.md](./DEBUG_LOG.md)

## API 文档

`http://localhost:8000/docs` — Swagger 交互式 API 文档
