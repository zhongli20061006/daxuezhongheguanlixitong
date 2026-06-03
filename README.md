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
│   ├── services/           # 业务逻辑层 (5 个)
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

## 快速开始

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

如需使用其他 25 个测试账号，运行 `python -m app.init_data` 重新初始化。

## 功能模块

| 模块 | 接口 | 状态 |
|------|------|------|
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
