# 全局视觉换新 v001

## 生命周期控制

- `schema`: `sliver-ui-prototype/v2`
- `active_version`: `v001`
- `prototype_status`: `approved`
- `approved_version`: `v001`
- `approval_mode`: `explicit: 用户在本轮对话确认"组合四·青紫幻光"交叉方案`
- `approval_evidence`: `v001，2026-08-03 对话批准，约束审查兼容`
- `implementation_version`: `v001`
- `implementation_status`: `verified`

## 需求来源

用户选择"整体视觉换新"（令牌层统一升级），不动布局结构、路由、组件行为与业务逻辑。

## 项目 UI 上下文（约束审查）

- 现有令牌所有者：`student-management-frontend/src/styles/global.css`（`:root` 设计令牌）
- 布局外壳：`AppNavbar.vue`（48px 渐变顶栏 + 200px 深色侧栏，移动端底部 Tab）
- 组件库：Element Plus；页面共用 `.content-card/.stat-card/.page-container` 等全局类
- 品牌：智伴校园（AI 智能体为招牌功能，首页即对话页）
- 现状：纯蓝主色、直角偏小、阴影偏硬、侧栏纯黑，整体偏"管理后台模板"气质

## 视觉方向：青紫幻光（青蓝→紫罗兰 × 暖橙/薄荷双点缀，已批准）

设计优先级：先让系统看起来"为一个 AI 校园助手而设计"，而非通用后台。

### 颜色

| 令牌 | 现值 | 目标值 | 说明 |
|------|------|--------|------|
| primary | #2563EB | #0EA5E9（青蓝） | 保留校园活力 |
| primary-light | #3B82F6 | #38BDF8 | 悬停 |
| primary-dark | #1D4ED8 | #0284C7 | 按下/激活 |
| accent 渐变 | 无 | 135deg #0EA5E9 → #6366F1 → #8B5CF6 | 青→靛→紫 AI 光谱 |
| 页面背景 | #F0F2F5 | #F8FAFC | 中性冷白衬底 |
| 侧栏 | #0F172A | 深青黑→深紫 #0F172A → #4C1D95 | 二、三组合并 |
| success/warning/danger/info | 现绿/橙/红/紫 | 保持色相，饱和度微调一致 | 语义色不换 |
| 点缀·暖橙 | 无 | #F97316：按钮 hover 光、进度条、徽标、限选强调 | 小面积使用 |
| 点缀·薄荷 | 无 | #10B981：成功态、已通过 | 小面积使用 |

### 形状与质感

| 令牌 | 现值 | 目标值 |
|------|------|--------|
| radius sm/md/lg/xl | 6/8/12/16 | 8/10/16/20 |
| 按钮圆角 | 6 | 8 |
| 卡片 padding | 20 | 24 |
| 阴影 | sm~xl 四档 | 更柔和：低透明度、大模糊、短 y 偏移（卡片 1px 边框 + 轻投影） |

### 排版

- 页面标题 22px 保持，字重 700→750 级感知（加粗），字距 -0.3px 保持
- 正文行高 1.6 保持；表格/按钮字号保持
- 智能体对话卡片：消息气泡改为青→紫渐变（自己）与白色卡片（模型），确认卡片加 accent 边框

### 明确不动

- 布局结构、路由、导航项、组件交互、功能逻辑、Element Plus 组件用法
- 响应式断点与移动端 Tab 结构
- 不改组件库、不引入第二套视觉系统

## 参考（仅借鉴方向，不照搬）

- Linear：克制 + 渐变点缀的现代感
- Lark：大圆角 + 清爽间距的办公感
- Vercel：轻阴影层级

## 验证计划

- `npm run build` 通过
- 逐页截图抽查（登录/首页智能体/课表/选课/管理端），确认无页面局部风格断裂
- 修改前后 diff 检查，确认只动令牌与视觉类样式

## 实施回写

- 实际改动：`global.css` 令牌与 Element Plus 主题变量、AppNavbar 侧栏/顶栏渐变、Agent 对话气泡与确认卡片、登录页、Dashboard/ChangePassword/Profile/Schedule/Scores/Selection/MyExams/Notifications 的硬编码旧蓝统一换新；侧栏右缘加柔和投影过渡、主背景加品牌色微光渐变（用户反馈迭代）。
- 验证：`npm run build` 通过（2026-08-03）；旧蓝扫描无残留。
- `未验证`：各页面在浏览器中的实际渲染观感需用户刷新后人工确认（设计保真度验收）。

## 构件清单（v001）

无二进制构件；本原型为令牌与视觉方向文档。
