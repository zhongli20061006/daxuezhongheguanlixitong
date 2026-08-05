# 智伴校园前端 UI 重构（现代学院风）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改任何业务逻辑的前提下，把智伴校园前端从"蓝紫渐变 AI 模板脸"重构为暖白 + 深青绿的现代学院风。

**Architecture:** 全部改动在 `student-management-frontend/` 内，采用"设计令牌 + Element Plus 全局覆盖"驱动：先重写 `global.css` 令牌层让所有页面自动换装，再精修外壳（AppNavbar）和三个核心页（Login / Dashboard / Agent），最后清理散落旧色值。不改路由、接口、Pinia store 的业务逻辑。

**Tech Stack:** Vue 3.4 / Vite 5 / Element Plus 2.5 / 原生 CSS 变量（无 Tailwind，不新增依赖）。

**Spec 依据:** `docs/superpowers/specs/2026-08-05-frontend-ui-redesign-design.md`（已提交，commit `487c936`）。

**仓库纪律（AGENTS.md）:**
- 所有 git 命令必须带 `-c safe.directory="D:/DjangoProject/学生管理系统（实验）"`
- 只 add 本任务明确列出的文件；禁止提交 `.omo/`、`.superpawers/`、`技术设计文档.docx`
- 验证只跑前端 `npm run build`，不跑后端 pytest，不启动服务
- 不读取 `docs/` 下除本计划与 spec 以外的文件

---

### Task 1: 设计令牌层（global.css 全量重写）

**Files:**
- Modify: `student-management-frontend/src/styles/global.css`（整个文件替换）

- [ ] **Step 1: 用以下内容整体替换 `global.css` 全部旧内容**

```css
/* ================================================================
   Design Tokens & Global Styles — 智伴校园（现代学院风）
   ================================================================ */

:root {
  /* ── Brand Colors ── */
  --color-primary: #0F766E;
  --color-primary-hover: #0B5F55;
  --color-primary-active: #095047;
  --color-primary-light: #3E9A91;
  --color-primary-bg: #E7F0EE;
  --color-accent: var(--color-primary);

  --color-success: #3F7D5E;
  --color-success-light: #6FA184;
  --color-success-bg: #EAF1E9;
  --color-warning: #B07D2A;
  --color-warning-light: #C99B5A;
  --color-warning-bg: #F7F0E2;
  --color-danger: #B4493C;
  --color-danger-light: #CF7568;
  --color-danger-bg: #F6EAE7;
  --color-info: #56739A;
  --color-info-bg: #EAEFF5;

  /* ── Neutral Palette (warm) ── */
  --color-bg: #F5F0E7;
  --color-bg-alt: #EFE9DD;
  --color-surface: #FFFDF9;
  --color-surface-hover: #FAF6EC;
  --color-border: #E6DED0;
  --color-border-light: #EFE9DD;

  --color-text-primary: #26221C;
  --color-text-secondary: #615B50;
  --color-text-tertiary: #756F63;
  --color-text-muted: #938C7E;
  --color-text-inverse: #FFFFFF;

  /* ── Shadow Levels (warm-tinted) ── */
  --shadow-xs: 0 1px 2px rgba(61, 55, 45, 0.05);
  --shadow-sm: 0 1px 3px rgba(61, 55, 45, 0.06), 0 1px 2px rgba(61, 55, 45, 0.04);
  --shadow-md: 0 4px 10px rgba(61, 55, 45, 0.07), 0 2px 4px rgba(61, 55, 45, 0.05);
  --shadow-lg: 0 12px 24px rgba(61, 55, 45, 0.09), 0 4px 8px rgba(61, 55, 45, 0.06);
  --shadow-xl: 0 24px 40px rgba(61, 55, 45, 0.10), 0 8px 16px rgba(61, 55, 45, 0.06);

  /* ── Border Radius ── */
  --radius-xs: 6px;
  --radius-sm: 8px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 18px;
  --radius-full: 9999px;

  /* ── Spacing ── */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;

  /* ── Transitions ── */
  --transition-fast: 150ms ease;
  --transition-base: 250ms ease;
  --transition-slow: 350ms ease;

  /* ── Element Plus Theme ── */
  --el-color-primary: #0F766E;
  --el-color-primary-light-3: #3E9A91;
  --el-color-primary-light-5: #6FB4AE;
  --el-color-primary-light-7: #A5CFCB;
  --el-color-primary-light-8: #C3DFDC;
  --el-color-primary-light-9: #E7F0EE;
  --el-color-primary-dark-2: #0B5F55;
  --el-color-success: #3F7D5E;
  --el-color-warning: #B07D2A;
  --el-color-danger: #B4493C;
  --el-color-error: #B4493C;
  --el-color-info: #56739A;
  --el-border-radius-base: 8px;
  --el-bg-color: #FFFDF9;
  --el-bg-color-overlay: #FFFDF9;
  --el-bg-color-page: #F5F0E7;
  --el-fill-color-blank: #FFFDF9;
  --el-fill-color-light: #F3EEE3;
  --el-fill-color-lighter: #F3EEE3;
  --el-fill-color-extra-light: #FAF6EC;
  --el-border-color: #E6DED0;
  --el-border-color-light: #E6DED0;
  --el-border-color-lighter: #EFE9DD;
  --el-border-color-extra-light: #EFE9DD;
  --el-text-color-primary: #26221C;
  --el-text-color-regular: #615B50;
  --el-text-color-secondary: #756F63;
  --el-text-color-placeholder: #938C7E;
  --el-text-color-disabled: #B4AC9C;
  --el-box-shadow: 0 12px 24px rgba(61, 55, 45, 0.09), 0 4px 8px rgba(61, 55, 45, 0.06);
  --el-box-shadow-light: 0 4px 10px rgba(61, 55, 45, 0.07), 0 2px 4px rgba(61, 55, 45, 0.05);
  --el-box-shadow-lighter: 0 1px 3px rgba(61, 55, 45, 0.06), 0 1px 2px rgba(61, 55, 45, 0.04);
  --el-table-border-color: #E6DED0;
  --el-table-header-bg-color: #EFE9DD;
  --el-table-header-text-color: #615B50;
  --el-table-row-hover-bg-color: #E7F0EE;
  --el-table-bg-color: #FFFDF9;
  --el-table-tr-bg-color: #FFFDF9;
  --el-table-expanded-cell-bg-color: #FAF6EC;
  --el-disabled-bg-color: #F3EEE3;
  --el-disabled-border-color: #E6DED0;
  --el-disabled-text-color: #B4AC9C;
  --el-mask-color: rgba(61, 55, 45, 0.35);
}

/* ── Reset & Base ── */
*,
*::before,
*::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  font-family: 'PingFang SC', 'HarmonyOS Sans SC', 'MiSans', 'Microsoft YaHei', 'Segoe UI', sans-serif;
  background:
    radial-gradient(1200px 520px at 88% -8%, rgba(15, 118, 110, 0.05), transparent 60%),
    radial-gradient(1000px 600px at -5% 105%, rgba(176, 125, 42, 0.05), transparent 60%),
    var(--color-bg);
  background-attachment: fixed;
  color: var(--color-text-primary);
  line-height: 1.6;
}

a {
  color: var(--color-primary);
  text-decoration: none;
  transition: color var(--transition-fast);
}
a:hover {
  color: var(--color-primary-hover);
}

/* ── Scrollbar ── */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: rgba(61, 55, 45, 0.18);
  border-radius: var(--radius-full);
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(61, 55, 45, 0.30);
}

/* ── Layout Helpers ── */
.page-container {
  padding: var(--space-lg) var(--space-xl);
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: var(--space-lg);
  flex-wrap: wrap;
}

.page-header-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
  background: var(--color-primary-bg);
  color: var(--color-primary);
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
  letter-spacing: -0.3px;
  line-height: 1.25;
}

.page-subtitle {
  font-size: 13px;
  color: var(--color-text-tertiary);
  margin-top: 4px;
}

/* ── Card System ── */
.content-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  box-shadow: var(--shadow-sm);
  margin-bottom: var(--space-md);
  transition: box-shadow var(--transition-base);
  border: 1px solid var(--color-border-light);
}

.content-card:hover {
  box-shadow: var(--shadow-md);
}

.card-accent {
  border-top: 3px solid var(--color-primary);
}
.card-accent--success {
  border-top-color: var(--color-success);
}
.card-accent--warning {
  border-top-color: var(--color-warning);
}
.card-accent--danger {
  border-top-color: var(--color-danger);
}
.card-accent--info {
  border-top-color: var(--color-info);
}

.card-left-accent {
  border-left: 4px solid var(--color-primary);
}
.card-left-accent--success {
  border-left-color: var(--color-success);
}
.card-left-accent--warning {
  border-left-color: var(--color-warning);
}
.card-left-accent--danger {
  border-left-color: var(--color-danger);
}

/* ── Stat Cards ── */
.stat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
}

.stat-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-xs);
  display: flex;
  align-items: center;
  gap: 16px;
  transition: transform var(--transition-base), box-shadow var(--transition-base);
  border: 1px solid var(--color-border-light);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.2;
  letter-spacing: -0.5px;
  font-variant-numeric: tabular-nums;
}

.stat-label {
  font-size: 13px;
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.stat-icon--blue   { background: var(--color-primary-bg); color: var(--color-primary); }
.stat-icon--green  { background: var(--color-success-bg); color: var(--color-success); }
.stat-icon--orange { background: var(--color-warning-bg); color: var(--color-warning); }
.stat-icon--red    { background: var(--color-danger-bg);  color: var(--color-danger); }
.stat-icon--purple { background: var(--color-info-bg);    color: var(--color-info); }

/* ── Button Enhancements ── */
.el-button {
  border-radius: var(--radius-sm);
  font-weight: 500;
  transition: all var(--transition-fast);
}

.el-button:hover {
  transform: translateY(-1px);
}

.el-button:active {
  transform: translateY(0);
}

.el-button--primary {
  background: var(--color-primary);
  border-color: var(--color-primary);
  box-shadow: 0 2px 8px rgba(15, 118, 110, 0.25);
}
.el-button--primary:hover {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
  box-shadow: 0 4px 12px rgba(15, 118, 110, 0.32);
}
.el-button--primary:active {
  background: var(--color-primary-active);
  border-color: var(--color-primary-active);
}
.el-button--success {
  box-shadow: 0 2px 6px rgba(63, 125, 94, 0.22);
}
.el-button--warning {
  box-shadow: 0 2px 6px rgba(176, 125, 42, 0.22);
}
.el-button--danger {
  box-shadow: 0 2px 6px rgba(180, 73, 60, 0.20);
}

/* ── Table Enhancements ── */
.el-table {
  border-radius: var(--radius-md);
  overflow: hidden;
}

.el-table th.el-table__cell {
  background: var(--color-bg-alt) !important;
  color: var(--color-text-secondary);
  font-weight: 600;
  font-size: 13px;
}

.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell {
  background: var(--color-bg-alt);
}

.el-table__body tr:hover > td.el-table__cell {
  background: var(--color-primary-bg) !important;
}

.el-table .cell {
  font-variant-numeric: tabular-nums;
}

/* ── Form Enhancements ── */
.el-input__wrapper,
.el-textarea__inner {
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  box-shadow: 0 0 0 1px var(--color-border) inset;
  transition: all var(--transition-fast);
}

.el-input__wrapper:hover {
  box-shadow: 0 0 0 1px #CFC7B8 inset;
}

.el-input__wrapper.is-focus {
  box-shadow: 0 0 0 1px var(--color-primary) inset, 0 0 0 3px rgba(15, 118, 110, 0.12) !important;
}

.el-select .el-input__wrapper {
  border-radius: var(--radius-sm);
}

/* ── Tag Enhancements ── */
.el-tag {
  border-radius: var(--radius-xs);
  font-weight: 500;
}

/* ── Dialog Enhancements ── */
.el-dialog {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  background: var(--color-surface);
}

.el-dialog__header {
  border-bottom: 1px solid var(--color-border-light);
  padding: 20px 24px 16px;
  margin-right: 0;
}

.el-dialog__title {
  font-weight: 700;
  font-size: 17px;
}

.el-dialog__footer {
  border-top: 1px solid var(--color-border-light);
  padding: 14px 24px;
}

/* ── Empty State ── */
.el-empty__description {
  color: var(--color-text-muted);
}

/* ── Tabs ── */
.el-tabs__nav-wrap::after {
  height: 1px;
  background: var(--color-border);
}

.el-tabs__item {
  font-weight: 500;
  transition: color var(--transition-fast);
}

.el-tabs__item.is-active {
  color: var(--color-primary);
}

/* ── Alert ── */
.el-alert {
  border-radius: var(--radius-md);
}

/* ── Popover / Dropdown / Message ── */
.el-popover,
.el-dropdown-menu,
.el-message-box {
  background: var(--color-surface);
  border-color: var(--color-border);
  box-shadow: var(--shadow-lg);
}

.el-message {
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
}

/* ── Loading ── */
.el-loading-mask {
  border-radius: var(--radius-md);
}

/* ── Utility Classes ── */
.text-muted {
  color: var(--color-text-muted);
}

.flex-between {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.flex-center {
  display: flex;
  align-items: center;
  justify-content: center;
}

.gap-sm { gap: var(--space-sm); }
.gap-md { gap: var(--space-md); }
.gap-lg { gap: var(--space-lg); }

.mb-sm { margin-bottom: var(--space-sm); }
.mb-md { margin-bottom: var(--space-md); }
.mb-lg { margin-bottom: var(--space-lg); }

/* ── Animations ── */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}

@keyframes scaleIn {
  from { opacity: 0; transform: scale(0.95); }
  to   { opacity: 1; transform: scale(1); }
}

.animate-fade-in-up { animation: fadeInUp 0.4s ease-out; }
.animate-fade-in { animation: fadeIn 0.3s ease-out; }
.animate-scale-in { animation: scaleIn 0.25s ease-out; }

.stagger-children > * {
  opacity: 0;
  animation: fadeInUp 0.4s ease-out forwards;
}
.stagger-children > *:nth-child(1) { animation-delay: 0s; }
.stagger-children > *:nth-child(2) { animation-delay: 0.06s; }
.stagger-children > *:nth-child(3) { animation-delay: 0.12s; }
.stagger-children > *:nth-child(4) { animation-delay: 0.18s; }
.stagger-children > *:nth-child(5) { animation-delay: 0.24s; }
.stagger-children > *:nth-child(6) { animation-delay: 0.30s; }

/* ── Page Transition ── */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* ── Responsive ── */
@media (max-width: 768px) {
  :root {
    --space-lg: 16px;
    --space-xl: 20px;
  }

  .page-container {
    padding: 16px;
  }

  .page-title {
    font-size: 20px;
  }

  .stat-cards {
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .stat-card {
    padding: 14px;
  }

  .stat-value {
    font-size: 22px;
  }
}

@media (max-width: 480px) {
  .stat-cards {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 2: 验证构建**

Run: `Push-Location student-management-frontend; npm run build; Pop-Location`
Expected: `✓ built in ...`（exit code 0，无编译错误）

- [ ] **Step 3: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add student-management-frontend/src/styles/global.css
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "style(frontend): 现代学院风设计令牌与 Element Plus 全局覆盖"
```

---

### Task 2: App.vue 基础样式去重

**Files:**
- Modify: `student-management-frontend/src/App.vue`（仅替换 `<style>` 块，模板与 script 不动）

- [ ] **Step 1: 把 App.vue 的 `<style>` 块整体替换为以下内容**

```html
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

/* ── Page transition ── */
.page-fade-enter-active, .page-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
```

说明：原 `body { font-family: 'Microsoft YaHei', ...; background: #f5f7fa; }` 已由 global.css 统一接管，删掉避免覆盖。

- [ ] **Step 2: 验证构建**

Run: `Push-Location student-management-frontend; npm run build; Pop-Location`
Expected: `✓ built in ...`（exit code 0）

- [ ] **Step 3: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add student-management-frontend/src/App.vue
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "style(frontend): 移除 App.vue 冗余 body 样式"
```

---

### Task 3: 布局外壳重做（AppNavbar.vue）

**Files:**
- Modify: `student-management-frontend/src/components/AppNavbar.vue`

该组件结构不动（顶栏/侧边栏/移动端底栏三个区域），只改两处模板和整个 `<style>` 块。script 完全不动。

- [ ] **Step 1: 模板——加入品牌标**

把 header-left 中：

```html
        <span class="header-title">智伴校园</span>
```

替换为：

```html
        <div class="brand-mark" aria-hidden="true">智</div>
        <span class="header-title">智伴校园</span>
```

- [ ] **Step 2: 模板——头像去掉圆形**

把头像 div：

```html
          <div class="avatar" :title="auth.name">{{ auth.name.charAt(0) }}</div>
```

替换为：

```html
          <div class="avatar" :title="auth.name">{{ auth.name.charAt(0) }}</div>
```

模板字符串不变，形状由 Step 3 的 CSS 决定（border-radius: 10px 方形圆角）。

- [ ] **Step 3: 把整个 `<style scoped>` 块替换为以下内容**

```css
/* ── Layout ── */
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg);
}

/* ── Header (56px) ── */
.app-header {
  height: 56px;
  min-height: 56px;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  z-index: 100;
  position: relative;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
}

.toggle-btn {
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: color var(--transition-fast), background var(--transition-fast);
  padding: 6px;
  border-radius: var(--radius-sm);
}
.toggle-btn:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-alt);
}

.header-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text-primary);
  white-space: nowrap;
  letter-spacing: 0.5px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.bell-btn {
  cursor: pointer;
  color: var(--color-text-secondary);
  line-height: 1;
  padding: 6px;
  border-radius: var(--radius-sm);
  transition: background var(--transition-fast), color var(--transition-fast);
}
.bell-btn:hover {
  background: var(--color-bg-alt);
  color: var(--color-text-primary);
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: var(--color-primary-bg);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition-fast);
}
.avatar:hover {
  background: #D7E7E4;
}

/* ── Body (sidebar + content) ── */
.app-body {
  display: flex;
  flex: 1;
  min-height: 0;
}

/* ── Sidebar ── */
.app-sidebar {
  width: 216px;
  min-height: calc(100vh - 56px);
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  transition: width var(--transition-base);
  overflow-y: auto;
  overflow-x: hidden;
  flex-shrink: 0;
  position: relative;
}

.app-sidebar.collapsed {
  width: 64px;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  padding: 12px 10px;
}

.sidebar-section {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sidebar-divider {
  height: 1px;
  background: var(--color-border-light);
  margin: 10px 8px;
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  text-decoration: none;
  font-size: 14px;
  transition: background var(--transition-fast), color var(--transition-fast);
  white-space: nowrap;
}
.sidebar-item:hover {
  background: var(--color-bg-alt);
  color: var(--color-text-primary);
}
.sidebar-item.active {
  background: var(--color-primary-bg);
  color: var(--color-primary);
  font-weight: 600;
}
.sidebar-item .el-icon {
  font-size: 20px;
  min-width: 20px;
}

.sidebar-label {
  opacity: 1;
  transition: opacity var(--transition-fast);
}

.app-sidebar.collapsed .sidebar-item {
  justify-content: center;
  padding: 12px 0;
}
.app-sidebar.collapsed .sidebar-label {
  display: none;
}

.sidebar-badge :deep(.el-badge__content) {
  border: none;
  font-size: 11px;
  height: 16px;
  line-height: 16px;
  min-width: 16px;
  padding: 0 4px;
}

/* ── Main Content ── */
.app-main {
  flex: 1;
  min-height: calc(100vh - 56px);
  transition: margin-left 0.25s ease;
  overflow-y: auto;
}

/* ── Mobile Bottom Tabs ── */
.mobile-tabs {
  display: none;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  height: 56px;
  z-index: 1000;
  align-items: center;
  justify-content: space-around;
  padding-bottom: env(safe-area-inset-bottom, 0);
}

.mobile-tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: var(--color-text-muted);
  text-decoration: none;
  font-size: 11px;
  transition: color var(--transition-fast);
  flex: 1;
  height: 100%;
  position: relative;
}
.mobile-tab.active {
  color: var(--color-primary);
}
.mobile-label {
  line-height: 1;
}

/* ── Notification popover ── */
.notif-item {
  padding: 8px 0;
  border-bottom: 1px solid var(--color-border-light);
  cursor: pointer;
}
.notif-item:last-child {
  border-bottom: none;
}
.notif-item:hover {
  background: var(--color-bg-alt);
}

.el-dropdown {
  line-height: 1;
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .app-sidebar {
    display: none;
  }
  .mobile-tabs {
    display: flex;
  }
  .app-main {
    padding-bottom: 56px;
  }
}
```

注意：删除旧的 `.sidebar-item.active` 左侧竖条/内阴影与逐项滑入动画；删除 `.app-sidebar::before` 顶部光晕与深色渐变背景。

- [ ] **Step 4: 验证构建**

Run: `Push-Location student-management-frontend; npm run build; Pop-Location`
Expected: `✓ built in ...`（exit code 0）

- [ ] **Step 5: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add student-management-frontend/src/components/AppNavbar.vue
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "style(frontend): 重做布局外壳为浅色学院风"
```

---

### Task 4: 登录页重做（Login.vue）

**Files:**
- Modify: `student-management-frontend/src/views/Login.vue`

script 完全不动（handleLogin / forgetPwd / authStore 逻辑保留）。

- [ ] **Step 1: 把整个 `<template>` 块替换为以下内容**

```html
<template>
  <div class="login-wrapper">
    <div class="login-card">
      <div class="brand-mark" aria-hidden="true">智</div>
      <h1 class="brand-title">智伴校园</h1>
      <p class="brand-subtitle">统一的校园服务入口</p>
      <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon closable @close="errorMsg=''" style="margin-bottom:16px" />
      <el-form @submit.prevent="handleLogin">
        <el-form-item>
          <el-input v-model="username" placeholder="学号或工号" size="large" @keyup.enter="handleLogin" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="password" type="password" show-password placeholder="密码" size="large" @keyup.enter="handleLogin" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" @click="handleLogin" class="login-btn">
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form-item>
      </el-form>
      <p class="forgot-pwd" @click="forgetPwd">忘记密码？</p>
      <p class="login-footer">© 2024 智伴校园</p>
    </div>
  </div>
</template>
```

- [ ] **Step 2: 把整个 `<style scoped>` 块替换为以下内容**

```css
.login-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: var(--color-bg);
}

.login-card {
  width: 100%;
  max-width: 400px;
  padding: 40px 36px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  text-align: center;
  animation: scaleIn 0.3s ease-out;
}

.brand-mark {
  width: 48px;
  height: 48px;
  margin: 0 auto 16px;
  border-radius: 14px;
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 700;
}

.brand-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 6px;
  letter-spacing: -0.3px;
}

.brand-subtitle {
  font-size: 13px;
  color: var(--color-text-tertiary);
  margin: 0 0 28px;
}

.login-btn {
  width: 100%;
  height: 46px;
  font-size: 15px;
}

.forgot-pwd {
  text-align: center;
  color: var(--color-text-muted);
  font-size: 13px;
  cursor: pointer;
  margin-top: 12px;
}
.forgot-pwd:hover {
  color: var(--color-primary);
}

.login-footer {
  text-align: center;
  color: var(--color-text-muted);
  font-size: 11px;
  margin-top: 20px;
}

:deep(.el-input__wrapper) {
  transition: box-shadow var(--transition-base), border-color var(--transition-base);
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--color-primary) inset, 0 0 0 3px rgba(15, 118, 110, 0.15) !important;
}

@media (max-width: 480px) {
  .login-card {
    padding: 32px 24px;
  }
}
```

注意：删除原 `.login-brand`、`.brand-pattern`、`.brand-dot`、`.form-card-accent` 等旧结构与渐变样式。

- [ ] **Step 3: 验证构建**

Run: `Push-Location student-management-frontend; npm run build; Pop-Location`
Expected: `✓ built in ...`（exit code 0）

- [ ] **Step 4: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add student-management-frontend/src/views/Login.vue
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "style(frontend): 登录页改为居中暖白卡片式"
```

---

### Task 5: 仪表盘重做（Dashboard.vue）

**Files:**
- Modify: `student-management-frontend/src/views/Dashboard.vue`

数据加载逻辑（loadData / 各 computed）完全不动，只改模板三处 + script 加一行日期 + 样式定向替换。

- [ ] **Step 1: 模板——问候区改为纯文字标题**

把整块：

```html
    <!-- Time-based Greeting -->
    <div class="greeting-card">
      <el-icon :size="24" class="greeting-icon">
        <Sunny v-if="greetingType === 'morning'" />
        <Coffee v-else-if="greetingType === 'afternoon'" />
        <Moon v-else />
      </el-icon>
      <span class="greeting-text">{{ greetingText }}，{{ auth.name || '用户' }}</span>
    </div>
```

替换为：

```html
    <!-- Time-based Greeting -->
    <div class="greeting-block">
      <h1 class="greeting-title">{{ greetingText }}，{{ auth.name || '用户' }}</h1>
      <p class="greeting-date">{{ todayText }}</p>
    </div>
```

- [ ] **Step 2: script——新增今天日期**

在 `const auth = useAuthStore()` 下一行加入：

```js
const todayText = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
```

- [ ] **Step 3: 模板——移除课表项内联蓝色**

把：

```html
            <div v-for="course in todayCourses" :key="course.id" class="schedule-item" :style="{ borderLeftColor: '#409EFF' }">
```

替换为：

```html
            <div v-for="course in todayCourses" :key="course.id" class="schedule-item">
```

- [ ] **Step 4: 模板——快捷入口改为横向链接行**

把整块 `<!-- Quick Entry Cards -->` 里的 `.quick-entries` div 替换为：

```html
    <!-- Quick Entry Links -->
    <div v-else class="quick-links">
      <div class="quick-link" @click="$router.push('/selection')">
        <el-icon :size="18"><Tickets /></el-icon>
        <span class="quick-label">选课中心</span>
        <span class="quick-meta">{{ enrolledCount }}门已选</span>
      </div>
      <div class="quick-link" @click="$router.push('/leaves')">
        <el-icon :size="18"><Document /></el-icon>
        <span class="quick-label">请假申请</span>
        <span class="quick-meta">{{ pendingLeaveCount }}条待批</span>
      </div>
      <div class="quick-link" @click="$router.push('/repairs')">
        <el-icon :size="18"><Tools /></el-icon>
        <span class="quick-label">报修维修</span>
        <span class="quick-meta">提交报修</span>
      </div>
    </div>
```

注意：保留外层 `v-if="pageLoading"` 的骨架屏版本不动（把它的 class 从 `quick-entries` 改为 `quick-links`，骨架块保持 `skeleton-entry-card`）。

- [ ] **Step 5: 样式——定向替换以下规则**

把 `.greeting-card` 至 `.greeting-text` 整块替换为：

```css
.greeting-block {
  margin-bottom: 24px;
}
.greeting-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.5px;
  margin: 0;
}
.greeting-date {
  font-size: 13px;
  color: var(--color-text-tertiary);
  margin: 6px 0 0;
}
```

把：

```css
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}
```

替换为：

```css
.dashboard-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}
```

把 `.card-schedule` / `.card-notification` 两条 border-top 规则删除（改为无顶部彩条）。

把 `.schedule-time` 的 `color: #409EFF;` 改为 `color: var(--color-primary);`。

把 `.view-all` 的 `color: #409EFF;` 改为 `color: var(--color-primary);`。

把 `.quick-entries` 至 `.entry-badge` 整块替换为：

```css
.quick-links {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.quick-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: border-color var(--transition-fast), color var(--transition-fast), background var(--transition-fast);
}
.quick-link:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-bg);
}
.quick-label {
  font-size: 14px;
  font-weight: 600;
}
.quick-meta {
  margin-left: auto;
  font-size: 12px;
  color: var(--color-text-muted);
}
```

把骨架屏中 `skeleton-entry-card` 的 class 引用同步改为 `skeleton-entry-card`（样式规则保留，仅颜色如 `#e5e7eb` 允许保留为占位灰）。

响应式：把 `@media (max-width: 768px)` 里的 `.quick-entries { grid-template-columns: 1fr; }` 改为 `.quick-links { grid-template-columns: 1fr; }`；`@media (max-width: 900px)` 的 `.dashboard-grid { grid-template-columns: 1fr; }` 保持。

- [ ] **Step 6: 验证构建**

Run: `Push-Location student-management-frontend; npm run build; Pop-Location`
Expected: `✓ built in ...`（exit code 0）

- [ ] **Step 7: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add student-management-frontend/src/views/Dashboard.vue
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "style(frontend): 仪表盘改为非对称网格与安静快捷入口"
```

---

### Task 6: AI 助手页重做（Agent.vue）

**Files:**
- Modify: `student-management-frontend/src/views/Agent.vue`

模板只改删除按钮可见性（纯 CSS 实现）与快捷提示样式，script 完全不动，`<style scoped>` 整体替换。

- [ ] **Step 1: 把整个 `<style scoped>` 块替换为以下内容**

```css
.agent-layout {
  display: flex;
  min-height: calc(100vh - 56px);
}

.session-panel {
  width: 220px;
  border-right: 1px solid var(--color-border);
  background: var(--color-surface);
  display: flex;
  flex-direction: column;
  padding: 12px;
  align-self: flex-start;
  position: sticky;
  top: 0;
  height: calc(100vh - 56px);
}

.session-panel-head {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  margin: 2px 2px 10px;
}

.new-session-btn {
  width: 100%;
  margin-bottom: 12px;
}

.session-list {
  flex: 1;
  overflow-y: auto;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  margin-bottom: 4px;
}
.session-item:hover {
  background: var(--color-bg-alt);
}
.session-item.active {
  background: var(--color-primary-bg);
}

.session-item .el-button {
  opacity: 0;
  transition: opacity var(--transition-fast);
}
.session-item:hover .el-button {
  opacity: 1;
}

.session-title {
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

.hero-area {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 24px;
  text-align: center;
}

.hero-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 10px 0 0;
  letter-spacing: -0.3px;
}

.hero-subtitle {
  color: var(--color-text-tertiary);
  font-size: 14px;
  margin: 0;
}

.hero-input {
  display: flex;
  gap: 10px;
  width: min(560px, 92%);
  margin-top: 8px;
}
.hero-input .el-input {
  flex: 1;
}
.hero-input .el-button {
  height: 46px;
  padding: 0 28px;
  border-radius: var(--radius-md);
}

.chat-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
  position: sticky;
  top: 0;
  z-index: 20;
}
.chat-header h2 {
  font-size: 16px;
  margin: 0;
  color: var(--color-text-primary);
}

.model-status {
  font-size: 12px;
  color: var(--color-warning);
}
.model-status.ok {
  color: var(--color-success);
}

.message-list {
  flex: 1;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.msg {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 12px;
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
  align-self: flex-start;
}

.msg.own {
  align-self: flex-end;
  background: var(--color-primary);
  color: #fff;
}
.msg.error {
  background: var(--color-danger-bg);
  color: var(--color-danger);
  border: 1px solid #E5C7C1;
}
.msg.summary {
  background: transparent;
  color: var(--color-text-muted);
  font-size: 12px;
  align-self: center;
}
.msg.typing {
  color: var(--color-text-muted);
  font-style: italic;
}

.msg-card {
  max-width: 80%;
  align-self: flex-start;
}

.confirm-card {
  border-top: 3px solid var(--color-primary);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-content pre {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
  font-family: inherit;
  font-size: 13px;
}

.table-scroll {
  max-height: 320px;
  overflow-y: auto;
}

.plan-box {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.plan-summary {
  margin: 0;
  font-weight: 600;
  color: var(--color-text-primary);
}

.plan-item {
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  background: var(--color-bg-alt);
}

.plan-item-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.plan-item-head strong {
  color: var(--color-text-primary);
  font-size: 14px;
}

.plan-duration {
  margin-left: auto;
  color: var(--color-text-muted);
  font-size: 12px;
}

.plan-line {
  margin: 3px 0;
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.plan-label {
  display: inline-block;
  min-width: 30px;
  margin-right: 6px;
  font-size: 12px;
  color: var(--color-primary);
  font-weight: 600;
}

.confirm-info {
  color: var(--color-text-secondary);
  font-size: 13px;
}

.confirm-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.quick-prompts {
  padding: 8px 20px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.prompt-tag {
  cursor: pointer;
  background: var(--color-primary-bg) !important;
  color: var(--color-primary) !important;
  border: none !important;
  border-radius: var(--radius-sm) !important;
  font-weight: 500;
}

.input-bar {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
  position: sticky;
  bottom: 0;
  z-index: 20;
}

@media (max-width: 768px) {
  .input-bar {
    bottom: 56px;
  }
}
```

- [ ] **Step 2: 验证构建**

Run: `Push-Location student-management-frontend; npm run build; Pop-Location`
Expected: `✓ built in ...`（exit code 0）

- [ ] **Step 3: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add student-management-frontend/src/views/Agent.vue
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "style(frontend): AI 助手页改为暖白聊天界面"
```

---

### Task 7: 品牌 logo 去多色化（AgentLogo.vue）

**Files:**
- Modify: `student-management-frontend/src/components/AgentLogo.vue`

模板不动，只替换 `<style scoped>` 块，把五彩 conic 渐变改为双青绿环。

- [ ] **Step 1: 把 `<style scoped>` 块替换为以下内容**

```css
.agent-logo {
  position: relative;
  width: 120px;
  height: 120px;
}

.logo-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: conic-gradient(from 0deg, #0F766E, #3E9A91, #0F766E);
  animation: logo-spin 6s linear infinite;
  -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 7px), #000 calc(100% - 6px));
  mask: radial-gradient(farthest-side, transparent calc(100% - 7px), #000 calc(100% - 6px));
}

.logo-orbit {
  position: absolute;
  inset: 8px;
  border-radius: 50%;
  animation: logo-spin 9s linear infinite reverse;
}

.orbit-dot {
  position: absolute;
  top: -4px;
  left: 50%;
  width: 9px;
  height: 9px;
  margin-left: -4.5px;
  border-radius: 50%;
  background: var(--color-primary);
  box-shadow: 0 0 10px rgba(15, 118, 110, 0.7);
}

.logo-core {
  position: absolute;
  inset: 22px;
  border-radius: 50%;
  background: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 14px 30px rgba(15, 118, 110, 0.32);
  animation: logo-breathe 3.2s ease-in-out infinite;
}

.logo-char {
  font-size: 44px;
  font-weight: 700;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.14);
}

@keyframes logo-spin {
  to { transform: rotate(360deg); }
}

@keyframes logo-breathe {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}
```

- [ ] **Step 2: 验证构建**

Run: `Push-Location student-management-frontend; npm run build; Pop-Location`
Expected: `✓ built in ...`（exit code 0）

- [ ] **Step 3: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add student-management-frontend/src/components/AgentLogo.vue
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "style(frontend): 品牌 logo 改为双青绿环"
```

---

### Task 8: 全局清理旧色值

**Files:** 按以下清单逐个处理（每处把十六进制旧色替换为对应 var() 令牌；渐变声明若含多个旧色则整个改为纯色令牌）：

- `student-management-frontend/src/views/Dashboard.vue`
- `student-management-frontend/src/views/Agent.vue`
- `student-management-frontend/src/views/Schedule.vue`
- `student-management-frontend/src/views/Profile.vue`
- `student-management-frontend/src/views/Login.vue`
- `student-management-frontend/src/views/Selection.vue`
- `student-management-frontend/src/views/Notifications.vue`
- `student-management-frontend/src/components/AgentLogo.vue`
- `student-management-frontend/src/components/ScheduleTable.vue`
- `student-management-frontend/src/views/ScoreInput.vue`
- `student-management-frontend/src/views/Repairs.vue`
- `student-management-frontend/src/views/MyExams.vue`
- `student-management-frontend/src/views/MyInvigilations.vue`
- `student-management-frontend/src/views/Leaves.vue`
- `student-management-frontend/src/views/Scores.vue`
- `student-management-frontend/src/views/ChangePassword.vue`
- `student-management-frontend/src/components/AppNavbar.vue`
- `student-management-frontend/src/styles/global.css`

替换映射表（全局适用，CSS 中直接写 var()，`:style` 内联处用 `var(--color-primary)` 字符串）：

| 旧值 | 新值 |
|---|---|
| `#409EFF` | `var(--color-primary)` |
| `#0EA5E9` | `var(--color-primary)` |
| `#6366F1` | `var(--color-primary)` |
| `#8B5CF6` | `var(--color-primary)` |
| `#F97316` | `var(--color-warning)` |
| `#E6A23C` | `var(--color-warning)` |
| `#D97706` / `#F59E0B` | `var(--color-warning)` |
| `#67C23A` / `#059669` / `#10B981` | `var(--color-success)` |
| `#DC2626` / `#EF4444` / `#B91C1C` | `var(--color-danger)` |
| `#0F172A` / `#155E75` / `#4C1D95` / `#1E40AF` / `#1E3A5F` | 深色渐变场景删除该渐变，改用 `var(--color-primary)` 或普通底色的对应令牌 |
| `#111827` / `#1F2937` / `#1E293B` | `var(--color-text-primary)` |
| `#374151` | `var(--color-text-secondary)` |
| `#6B7280` | `var(--color-text-tertiary)` |
| `#9CA3AF` | `var(--color-text-muted)` |
| `#F3F4F6` / `#F8FAFC` / `#F1F5F9` / `#F9FAFB` | `var(--color-bg-alt)` |
| `#E5E7EB` / `#f0f0f0` | `var(--color-border)` 或 `var(--color-border-light)`（细分割线用 light） |

注意事项：
- 骨架屏占位灰 `#e5e7eb` / `#f3f4f6` 允许保留（属于加载占位，不是品牌色）
- `global.css` 中新令牌本身（`#0F766E`、`#3E9A91`、`#6FB4AE`、`#A5CFCB`、`#C3DFDC`、`#E7F0EE`、`#0B5F55`、`#095047`、`#F5F0E7`、`#FFFDF9`、`#E6DED0`、`#EFE9DD` 等）不属于旧色，禁止改动
- 逐个文件处理完后立即保存，不要一次处理多个文件

- [ ] **Step 1: 用以下命令找出全部旧色残留（改完一个文件跑一次）**

Run:
```powershell
Get-ChildItem -Path "D:\DjangoProject\学生管理系统（实验）\student-management-frontend\src" -Recurse -Include *.vue,*.css -File | Select-String -Pattern '#409EFF','#E6A23C','#67C23A','#0EA5E9','#6366F1','#8B5CF6','#F97316','#0F172A','#155E75','#4C1D95','#1E40AF','#1E3A5F','#1F2937','#6B7280','#9CA3AF','#F3F4F6','#F8FAFC','#F1F5F9','#111827','#374151','#D97706','#F59E0B','#059669','#DC2626','#E5E7EB'
```
Expected: 输出为空（0 条匹配）

- [ ] **Step 2: 验证构建**

Run: `Push-Location student-management-frontend; npm run build; Pop-Location`
Expected: `✓ built in ...`（exit code 0）

- [ ] **Step 3: 提交**

```bash
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" add student-management-frontend/src
git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" commit -m "style(frontend): 清理散落旧色值统一走设计令牌"
```

---

### Task 9: 最终验收

**Files:** 无（只验证与收尾）

- [ ] **Step 1: 构建验证**

Run: `Push-Location student-management-frontend; npm run build; Pop-Location`
Expected: `✓ built in ...`，exit code 0

- [ ] **Step 2: 旧色值零残留验证**

Run: 同 Task 8 Step 1 的命令
Expected: 输出为空

- [ ] **Step 3: 手动冒烟检查清单（本地 `npm run dev` 后浏览器验证）**

- 登录页：居中暖白卡片、青绿品牌标、无渐变
- 登录后：浅色顶栏 + 浅色侧边栏，当前菜单项为青绿浅底
- 仪表盘：文字问候区、4 个统计卡、2/3+1/3 网格、横向快捷链接
- AI 助手：hero 区双青绿环 logo、青绿消息气泡、会话删除按钮 hover 才显示
- 缩放窗口到 <768px：侧边栏消失、底部 tab 出现且为暖白
- 表格/弹窗/输入框：暖沙边框、青绿 focus 描边
- 全站无残留蓝紫渐变或 `#409EFF`

- [ ] **Step 4: 确认工作区干净（除 .omo/.superpawers/技术设计文档.docx 等 gitignore/禁提交项）**

Run: `git -c safe.directory="D:/DjangoProject/学生管理系统（实验）" status -sb`
Expected: 无未提交的 src 改动；若还有，按 Task 8 Step 3 补提交

- [ ] **Step 5: 收尾说明**

向用户汇报：重构完成、构建通过、冒烟清单结果；说明其余页面（Schedule/Scores/Selection 等）已通过全局令牌继承新风格，若需逐页精修可作为后续任务。

---

## Self-Review（计划自检）

**Spec 覆盖：**
- 设计令牌（颜色/字体/圆角/阴影/间距/动效）→ Task 1
- 字体与 tabular-nums → Task 1（body、.stat-value、.el-table .cell）
- 布局外壳（顶栏/侧边栏/移动端/页面容器）→ Task 3 + Task 2
- 登录页 → Task 4
- 仪表盘 → Task 5
- AI 助手 → Task 6 + Task 7
- Element Plus 全局覆盖 → Task 1（--el-* 变量 + 组件覆盖段）
- 清理写死旧色值 → Task 8
- 验证与验收 → 每个任务含 build + Task 9

**占位符扫描：** 无 TBD/TODO/"适当处理"类描述；所有代码步骤均给出完整代码。

**一致性检查：** 令牌名（--color-primary、--color-bg、--color-border 等）在 Task 1 定义，Task 3–8 全部引用同一批名字；AgentLogo 用的 `#0F766E`/`#3E9A91` 与 Task 1 主色一致；Dashboard 快捷链接 class（quick-links/quick-link/quick-label/quick-meta）在 Task 5 定义与引用一致。
