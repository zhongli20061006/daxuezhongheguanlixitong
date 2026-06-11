# 调试记录

## 压力测试（2026-06-02）

### 测试目的
模拟大规模并发使用场景，检测系统可靠性、数据一致性、竞态条件。

### 测试场景

| # | 场景 | 并发数 | 关键检测 |
|---|------|--------|----------|
| 1 | 选课抢课 | 50 学生 → schedule_id=5 (容量=50) | CAS UPDATE `WHERE enrolled < capacity` 防超售 |
| 2 | 教室预约 | 20 用户 → D401 同一时段 | 防重复预约 |
| 3 | 请假审批 | 5 教师 → 同一请假申请 | 防重复审批 |
| 4 | 考试生成 + 毕业审核 | 批量操作 | 数据完整性 |
| 5 | API 健康检查 | 8 核心端点 | 可用性 |
| 6 | 数据一致性检查 | 全表 | enrolled/capacity 一致性 |

### 场景 1：选课 CAS — ✅ 首次通过

50 人并发抢 50 名额：
```
并发请求: 50
成功选课: 50
失败(满额): 0
最终 enrolled: 50 = capacity: 50 ✅
```

**结论**：`UPDATE course_capacity SET enrolled = enrolled + 1 WHERE schedule_id=? AND enrolled < capacity` 原子操作有效，未出现幻读。

### 场景 2：教室预约 — ❌ 初版失败 → ✅ 修复后通过

**初版测试**：
```
并发请求: 20
成功预约: 8（预期 1）❌
```

**根因**：`SELECT 检查是否已预约` → `INSERT 预约记录` 不是原子操作，TOCTOU 竞态。

**修复方案**：在 `classroom_reservation` 表加 UNIQUE INDEX：
```sql
CREATE UNIQUE INDEX uk_reserve ON classroom_reservation(classroom_id, week, day_of_week, period);
```
改为 INSERT → 捕获 IntegrityError → 返回 409。

**修复后验证**：
```
并发请求: 20
成功预约: 1 ✅
失败(冲突): 19
```

### 场景 3：请假审批 — ❌ 初版失败 → ✅ 修复后通过

**初版测试**：
```
并发请求: 5
成功审批: 5（预期 1）❌
审批记录数: 5
```

**根因**：添加审批记录 `ApprovalRecord` 时无唯一性约束，5 个并发请求各自插入成功。

**修复方案**：在 `approval_record` 表加 UNIQUE INDEX：
```sql
CREATE UNIQUE INDEX uk_approve ON approval_record(leave_id, level);
```
改为 `db.add(record) → db.flush()` → 捕获 IntegrityError → raise ValueError。

**修复后验证**：
```
并发请求: 5
成功审批: 1 ✅
审批记录数: 1
失败(重复): 4
```

### 场景 4-6：批量操作 + 健康检查 + 数据一致性 — ✅ 全部通过

### 结论

系统核心并发控制机制有效。发现并修复了 2 个 TOCTOU 竞态条件：
1. 教室预约：SELECT-then-INSERT → 改为 UNIQUE INDEX + INSERT IGNORE 模式
2. 请假审批：重复审批 → UNIQUE INDEX 保证幂等性

---

## 历史 E2E 测试记录

| 日期 | 版本 | 通过/总数 | 备注 |
|------|------|-----------|------|
| 2026-05-28 | v0.3 | 28/29 | 首次全流程 (1个设计预期差异) |
| 2026-05-28 | v0.3.1 | 16/16 | 选课+请假+通知修复后 |
| 2026-06-01 | v0.4 | 5/5 | 培养方案+毕业审核 |
| 2026-06-02 | v0.7 | 4/4 | 考试系统 |
| 2026-06-02 | v0.7.1 | 6/6 | 成绩教师端修复 |
| 2026-06-02 | v0.7.4 | 8/8 | 压力测试 + 竞态修复 |

---

## 已知问题（v0.4.0 已全部修复）

1. ~~**Element Plus 2.5.x `el-date-picker` + `value-format` 兼容性问题**~~ → ✅ v0.7.1 已修复（改用原生 `<input type="date">`）
2. ~~**SAEnum 与 MySQL ENUM 不兼容**~~ → ✅ 已修复（`Score.score_type`、`Repair.type`、`Repair.status` 使用 `String` 替代 `SAEnum`）
3. ~~**教师 `role_id` 存储工号（如 `"T10001"`）而非数字 ID**~~ → ✅ 已修复（`_get_teacher_id` 通过 `Teacher.job_number` 查表获取数字 ID）