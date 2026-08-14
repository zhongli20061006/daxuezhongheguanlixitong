# 设计真档索引

本项目 UI 原型与视觉方向的真档根。每个功能一个原型目录，版本不可覆盖。

## 现行方向（已实施）
- **现代学院风**（2026-08-05 重构，已落地）：暖白 + 深青绿单一主色，删除蓝紫渐变。
  - 计划：`../plans/2026-08-05-frontend-ui-redesign.md`
  - 规格：`../specs/2026-08-05-frontend-ui-redesign-design.md`
  - 实现：`student-management-frontend/src/styles/global.css`（设计令牌）

## 历史版本（已被取代，仅作参考）
- [全局视觉换新 v001（青紫幻光）](./prototypes/ui-refresh/v001/prototype.md) — 2026-08-05 起被"现代学院风"反向取代，不再作为实现依据。

> 2026-08-03 追加实现：智能体首页欢迎态（居中动态 Logo + 输入框，发消息后切换对话页），
> 历史会话侧栏常驻并与对话区视觉区分。见 `student-management-frontend/src/views/Agent.vue`。
