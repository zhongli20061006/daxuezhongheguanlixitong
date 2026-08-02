<template>
  <div class="app-layout">
    <!-- Header Bar (48px) -->
    <header class="app-header">
      <div class="header-left">
        <el-icon class="toggle-btn" :size="20" @click="collapsed = !collapsed">
          <Fold v-if="!collapsed" />
          <Expand v-else />
        </el-icon>
        <span class="header-title">大学生管理系统</span>
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

    <!-- Mobile Bottom Tabs (≤768px) -->
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

/* ───── Menu items by role ───── */
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

/* ───── Mobile bottom tabs ───── */
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

/* ───── Active route matching ───── */
function isActive(path) {
  return route.path === path || route.path.startsWith(path + '/')
}

/* ───── Event handlers ───── */
function handleCommand(cmd) {
  if (cmd === 'profile') router.push('/profile')
  else if (cmd === 'logout') { auth.logout(); router.push('/login') }
}

function goNotifications() { router.push('/notifications') }

/* ───── Notification logic ───── */
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
  ws = new WebSocket(`${protocol}://${window.location.hostname}:8000/ws?token=${auth.token}`)
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
/* ───── Layout ───── */
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

/* ───── Header (48px) ───── */
.app-header {
  height: 48px;
  min-height: 48px;
  background: var(--color-header-bg);
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  z-index: 100;
  position: relative;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toggle-btn {
  cursor: pointer;
  color: rgba(255,255,255,0.8);
  transition: color var(--transition-fast), background var(--transition-fast);
  padding: 4px;
  border-radius: var(--radius-sm);
}
.toggle-btn:hover {
  color: #fff;
  background: rgba(255,255,255,0.1);
}

.header-title {
  font-size: 16px;
  font-weight: 700;
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
  line-height: 1;
  padding: 4px;
  border-radius: var(--radius-sm);
  transition: background var(--transition-fast);
}
.bell-btn:hover {
  background: rgba(255,255,255,0.1);
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(255,255,255,0.2);
  border: 1px solid rgba(255,255,255,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: #fff;
  cursor: pointer;
  transition: background var(--transition-fast), border-color var(--transition-fast);
}
.avatar:hover {
  background: rgba(255,255,255,0.3);
  border-color: rgba(255,255,255,0.4);
}

/* ───── Body (sidebar + content) ───── */
.app-body {
  display: flex;
  flex: 1;
  min-height: 0;
}

/* ───── Sidebar ───── */
.app-sidebar {
  width: 200px;
  min-height: calc(100vh - 48px);
  background: var(--color-sidebar-bg);
  transition: width var(--transition-base);
  overflow-y: auto;
  overflow-x: hidden;
  flex-shrink: 0;
  position: relative;
}

/* Subtle glow gradient at the top of the sidebar */
.app-sidebar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: linear-gradient(180deg, rgba(37,99,235,0.08) 0%, transparent 100%);
  pointer-events: none;
}

.app-sidebar.collapsed {
  width: 60px;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  padding: 8px 0;
}

.sidebar-section {
  display: flex;
  flex-direction: column;
}

.sidebar-divider {
  height: 1px;
  background: rgba(255,255,255,0.08);
  margin: 8px 12px;
}

/* ───── Sidebar Items ───── */
.sidebar-item {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  color: rgba(255,255,255,0.65);
  cursor: pointer;
  text-decoration: none;
  font-size: 14px;
  transition: background var(--transition-fast), color var(--transition-fast), border-color var(--transition-fast), box-shadow var(--transition-fast);
  border-left: 3px solid transparent;
  white-space: nowrap;
}
.sidebar-item:hover {
  background: var(--color-sidebar-hover);
  color: #fff;
}
.sidebar-item.active {
  background: linear-gradient(90deg, rgba(37,99,235,0.12) 0%, rgba(37,99,235,0.04) 100%);
  color: #fff;
  border-left-color: var(--color-primary-light);
  box-shadow: inset 4px 0 0 0 var(--color-primary-light);
}
.sidebar-item .el-icon {
  font-size: 20px;
  margin-right: 12px;
  min-width: 20px;
}

.sidebar-label {
  opacity: 1;
  transition: opacity var(--transition-fast);
}

/* Collapsed state */
.app-sidebar.collapsed .sidebar-item {
  justify-content: center;
  padding: 14px 0;
}
.app-sidebar.collapsed .sidebar-item .el-icon {
  margin-right: 0;
}
.app-sidebar.collapsed .sidebar-label {
  display: none;
}

/* Sidebar badge (通知中心) */
.sidebar-badge :deep(.el-badge__content) {
  border: none;
  font-size: 11px;
  height: 16px;
  line-height: 16px;
  min-width: 16px;
  padding: 0 4px;
}

/* ───── Staggered Slide-in for Sidebar Items ───── */
@keyframes sidebarItemFadeIn {
  from {
    opacity: 0;
    transform: translateX(-16px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.sidebar-section .sidebar-item {
  animation: sidebarItemFadeIn 0.45s ease both;
}
.sidebar-section .sidebar-item:nth-child(1)  { animation-delay: 0s; }
.sidebar-section .sidebar-item:nth-child(2)  { animation-delay: 0.04s; }
.sidebar-section .sidebar-item:nth-child(3)  { animation-delay: 0.08s; }
.sidebar-section .sidebar-item:nth-child(4)  { animation-delay: 0.12s; }
.sidebar-section .sidebar-item:nth-child(5)  { animation-delay: 0.16s; }
.sidebar-section .sidebar-item:nth-child(6)  { animation-delay: 0.20s; }
.sidebar-section .sidebar-item:nth-child(7)  { animation-delay: 0.24s; }
.sidebar-section .sidebar-item:nth-child(8)  { animation-delay: 0.28s; }
.sidebar-section .sidebar-item:nth-child(9)  { animation-delay: 0.32s; }
.sidebar-section .sidebar-item:nth-child(10) { animation-delay: 0.36s; }

/* ───── Main Content ───── */
.app-main {
  flex: 1;
  min-height: calc(100vh - 48px);
  transition: margin-left 0.25s ease;
  overflow-y: auto;
}

/* ───── Mobile Bottom Tabs ───── */
.mobile-tabs {
  display: none;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--color-sidebar-bg);
  border-top: 1px solid rgba(255,255,255,0.06);
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
  color: rgba(255,255,255,0.5);
  text-decoration: none;
  font-size: 11px;
  transition: color var(--transition-fast);
  flex: 1;
  height: 100%;
  position: relative;
  border-top: 2px solid transparent;
}
.mobile-tab.active {
  color: var(--color-primary-light);
  border-top-color: var(--color-primary-light);
}
.mobile-label {
  line-height: 1;
}

/* ───── Responsive ───── */
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
  .app-main.collapsed {
    /* no sidebar on mobile, so no margin change needed */
  }
}

/* ───── Notification popover (inherited style) ───── */
.notif-item {
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
}
.notif-item:last-child {
  border-bottom: none;
}
.notif-item:hover {
  background: #f9fafb;
}

/* ───── Element Plus dropdown trigger inline fix ───── */
.el-dropdown {
  line-height: 1;
}
</style>
