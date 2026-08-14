# 安全与质量修复计划（2026-08-14）

> 来源：2026-08-14 全项目审查（项目体检）。用户授权：修复批准；root 密码在真实使用（不轮换、不改写 git 历史）；部署目标仅实验展示。

## 阶段 1：后端访问控制修复
- B1 请假审批水平越权：辅导员仅能审批本班学生（service 层校验，REST + Agent 双路径生效）
- B2 跨班选课：enroll 与 Agent `_resolve_schedule` 增加班级归属校验

## 阶段 2：正确性修复
- B5 退课→重选→再退课 500：enroll 复用 status=0 记录（UPDATE）而非盲目 INSERT

## 阶段 3：数据库约束恢复
- B3 教室预约唯一约束：去重（保留最新）→ 新 alembic 迁移重建唯一索引 → 模型补 UniqueConstraint
- B4 审批幂等约束：同上；ApprovalRequest.result 增加枚举校验

## 阶段 4：密钥/部署/前端小修（实验展示定位）
- `命令` 文件去密（保留交互式输入）；本地 .env 换新随机 SECRET_KEY
- 后端 fail-closed：config 校验密钥长度/弱默认值；compose 用 `:?` 强制注入
- .env.docker 补 OLLAMA_BASE_URL + compose host-gateway；MySQL 端口绑 127.0.0.1
- .gitignore 补 .omo/.superpawers/pytest 缓存/备份 SQL/根 docx
- 前端 B8 401 假死 + B3 登录态信任 localStorage（checkAuth 接服务端）；WS 去硬编码端口
- 清理权限异常的 pytest-cache-files-* 目录

## 阶段 5：文档真相修复
- 测试数 154、结构数字 16 路由/21 模型文件/12 schema；设计方向索引更新
- DEBUG_LOG 版本矛盾、E2E 数字更正；docker-init 补 agent01；README 补 Docker-Ollama 说明

## 验收与停止条件
- 每阶段：后端 pytest 全绿 + 前端构建通过 + 本地 Git 提交（不推送）
- 阶段 3 去重前必须备份表；任何验证失败即停下汇报
