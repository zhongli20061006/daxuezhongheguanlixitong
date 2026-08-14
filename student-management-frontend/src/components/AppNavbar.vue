<template>
  <div class="app-layout">
    <!-- Header Bar (56px) -->
    <header class="app-header">
      <div class="header-left">
        <el-icon class="toggle-btn" :size="20" @click="collapsed = !collapsed">
          <Fold v-if="!collapsed" />
          <Expand v-else />
        </el-icon>
        <div class="brand-mark" aria-hidden="true">智</div>
        <span class="header-title">智伴校园</span>
      </div>
      <div class="header-right">
        <el-popover placement="bottom" :width="360" trigger="click">
          <template #reference>
            <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99" class="bell-btn">
              <el-icon :size="20" style="cursor:pointer"><Bell /></el-icon>
            </el-badge>
          </template>
          <div style="max-height:350px;overflow-y:auto">
            <div v-for="n in latestNotifications" :key="n.id" class="notif-item" @click="goNotifications">
              <div style="font-weight:600;font-size:13px">{{ n.title }}</div>
              <div style="font-size:12px;color:#666">{{ n.content }}</div>
              <div style="font-size:11px;color:#999;margin-top:4px">{{ n.created_at }}</div>
            </div>
            <el-empty v-if="!latestNotifications.length" description="暂无通知" />
            <el-divider style="margin:8px 0" />
            <div style="display:flex;justify-content:space-between">
              <el-button text size="small" @click="goNotifications">查看全部</el-button>
              <el-button text size="small" @click="markAllRead" v-if="unreadCount > 0">全部已读</el-button>
            </div>
          </div>
        </el-popover>
        <el-dropdown trigger="click" @command="handleCommand">
          <div class="avatar" :title="auth.name">{{ auth.name.charAt(0) }}</div>
          <template #dropdown>
            <el-dropdown-item command="profile">个人中心</el-dropdown-item>
            <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
          </template>
        </el-dropdown>
      </div>
    </header>

    <!-- Body: Sidebar + Content -->
    <div class="app-body">
      <!-- Sidebar -->
      <aside class="app-sidebar" :class="{ collapsed }">
        <nav class="sidebar-nav">
          <!-- Role-specific menu items -->
          <div class="sidebar-section">
            <router-link
              v-for="item in menuItems"
              :key="item.path"
              :to="item.path"
              class="sidebar-item"
              :class="{ active: isActive(item.path) }"
            >
              <el-icon><component :is="item.icon" /></el-icon>
              <span class="sidebar-label">{{ item.label }}</span>
            </router-link>
          </div>

          <!-- Divider + common items -->
          <div class="sidebar-divider"></div>
          <div class="sidebar-section">
            <router-link
              to="/notifications"
              class="sidebar-item"
              :class="{ active: isActive('/notifications') }"
            >
              <el-icon>
                <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99" class="sidebar-badge">
                  <Bell />
                </el-badge>
              </el-icon>
              <span class="sidebar-label">通知中心</span>
            </router-link>
            <router-link
              to="/profile"
              class="sidebar-item"
              :class="{ active: isActive('/profile') }"
            >
              <el-icon><User /></el-icon>
              <span class="sidebar-label">个人中心</span>
            </router-link>
          </div>
        </nav>
      </aside>

      <!-- Main Content -->
      <main class="app-main" :class="{ collapsed }">
        <slot />
      </main>
    </div>

    <!-- Mobile Bottom Tabs (56px) -->
    <div class="mobile-tabs">
      <router-link
        v-for="tab in mobileTabs"
        :key="tab.path"
        :to="tab.path"
        class="mobile-tab"
        :class="{ active: isActive(tab.path) }"
      >
        <el-icon :size="22">
          <el-badge
            v-if="tab.badge"
            :value="unreadCount"
            :hidden="unreadCount === 0"
            :max="99"
          >
            <component :is="tab.icon" />
          </el-badge>
          <component v-else :is="tab.icon" />
        </el-icon>
        <span class="mobile-label">{{ tab.label }}</span>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import router from '../router'
import {
  HomeFilled, Calendar, Tickets, Document, OfficeBuilding,
  DataAnalysis, Reading, Tools, Timer, Bell, User, ChatDotRound,
  Management, Expand, Fold
} from '@element-plus/icons-vue'
import { getNotifications, getUnreadCount, markAllRead as markAllReadApi } from '../api/notification'

const auth = useAuthStore()
const route = useRoute()
const collapsed = ref(false)
const unreadCount = ref(0)
const latestNotifications = ref([])
let ws = null
let pollTimer = null

/* ── Menu items by role ── */
const menuItems = computed(() => {
  const role = auth.role
  const agentItem = { path: '/', label: 'AI 助手', icon: ChatDotRound }
  const menus = {
    student: [
      { path: '/dashboard',    label: '首页',       icon: HomeFilled },
      { path: '/schedule',     label: '课表',       icon: Calendar },
      { path: '/selection',    label: '选课中心',    icon: Tickets },
      { path: '/leaves',       label: '请假申请',    icon: Document },
      { path: '/classrooms',   label: '空闲教室',    icon: OfficeBuilding },
      { path: '/scores',       label: '我的成绩',    icon: DataAnalysis },
      { path: '/plan',         label: '培养方案',    icon: Reading },
      { path: '/repairs',      label: '报修中心',    icon: Tools },
      { path: '/my-exams',     label: '我的考试',    icon: Timer },
    ],
    teacher: [
      { path: '/classrooms',       label: '空闲教室',    icon: OfficeBuilding },
      { path: '/scores/input',     label: '成绩录入',    icon: DataAnalysis },
      { path: '/advisor',          label: '请假审批',    icon: Management },
      { path: '/repairs',          label: '报修中心',    icon: Tools },
      { path: '/my-invigilations', label: '监考安排',    icon: Timer },
    ],
    staff: [
      { path: '/classrooms',    label: '空闲教室',    icon: OfficeBuilding },
      { path: '/repairs/manage', label: '报修管理',    icon: Tools },
      { path: '/repairs',       label: '报修中心',    icon: Tools },
    ],
    admin: [
      { path: '/admin',          label: '管理后台',    icon: Management },
      { path: '/advisor',        label: '请假审批',    icon: Management },
      { path: '/repairs/manage', label: '报修管理',    icon: Tools },
      { path: '/classrooms',     label: '空闲教室',    icon: OfficeBuilding },
      { path: '/repairs',        label: '报修中心',    icon: Tools },
    ],
  }
  for (const key of Object.keys(menus)) {
    menus[key] = [agentItem, ...menus[key]]
  }
  return menus[role] || []
})

/* ── Mobile bottom tabs ── */
const mobileTabs = computed(() => {
  const role = auth.role
  const defaultPage = '/'

  let secondTab
  switch (role) {
    case 'student': secondTab = { path: '/schedule', label: '课表', icon: Calendar }; break
    case 'teacher': secondTab = { path: '/scores/input', label: '成绩', icon: DataAnalysis }; break
    case 'staff':   secondTab = { path: '/repairs/manage', label: '管理', icon: Tools }; break
    default:        secondTab = { path: '/admin', label: '管理', icon: Management }
  }

  return [
    { path: defaultPage, label: '首页', icon: HomeFilled },
    secondTab,
    { path: '/notifications', label: '通知', icon: Bell, badge: true },
    { path: '/profile', label: '我的', icon: User },
  ]
})

/* ── Active route matching ── */
function isActive(path) {
  return route.path === path || route.path.startsWith(path + '/')
}

/* ── Event handlers ── */
function handleCommand(cmd) {
  if (cmd === 'profile') router.push('/profile')
  else if (cmd === 'logout') { auth.logout(); router.push('/login') }
}

function goNotifications() { router.push('/notifications') }

/* ── Notification logic ── */
async function loadNotifications() {
  try {
    const [unreadRes, listRes] = await Promise.all([
      getUnreadCount(),
      getNotifications(5, 0),
    ])
    unreadCount.value = typeof unreadRes === 'number' ? unreadRes : (unreadRes?.count ?? 0)
    latestNotifications.value = listRes.notifications || []
  } catch { /* ignore */ }
}

async function markAllRead() {
  try { await markAllReadApi(); unreadCount.value = 0 } catch { /* ignore */ }
}

function connectWS() {
  if (!auth.token) return
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  // 同源连接：开发走 vite 代理(/ws)，生产走 nginx 反代(/ws)，不硬编码后端端口
  ws = new WebSocket(`${protocol}://${window.location.host}/ws?token=${auth.token}`)
  ws.onmessage = (e) => {
    try {
      const m = JSON.parse(e.data)
      if (m.type === 'notification') unreadCount.value++
    } catch { /* ignore */ }
  }
  ws.onclose = () => { setTimeout(connectWS, 5000) }
}

onMounted(() => {
  loadNotifications()
  connectWS()
  pollTimer = setInterval(loadNotifications, 30000)
})

onUnmounted(() => {
  if (ws) ws.close()
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
/* ── Layout ── */
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(1200px 520px at 88% -8%, rgba(37, 99, 235, 0.05), transparent 60%),
    radial-gradient(1000px 600px at -5% 105%, rgba(176, 125, 42, 0.06), transparent 60%),
    var(--color-bg);
  background-attachment: fixed;
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
  background: var(--gradient-tech);
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
</style>
