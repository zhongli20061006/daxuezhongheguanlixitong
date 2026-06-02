<template>
  <div class="navbar">
    <div class="nav-inner">
      <div class="nav-left">
        <el-button class="hamburger" text @click="mobileOpen = !mobileOpen" v-if="mobile">☰</el-button>
        <span class="nav-brand">大学生管理系统</span>
      </div>
      <div class="nav-center" v-if="!mobile">
        <template v-if="auth.role === 'student'">
          <router-link to="/schedule" class="nav-item">我的课表</router-link>
          <router-link to="/selection" class="nav-item">选课中心</router-link>
          <router-link to="/leaves" class="nav-item">请假申请</router-link>
          <router-link to="/classrooms" class="nav-item">空闲教室</router-link>
          <router-link to="/scores" class="nav-item">我的成绩</router-link>
          <router-link to="/plan" class="nav-item">培养方案</router-link>
          <router-link to="/repairs" class="nav-item">报修中心</router-link>
          <router-link to="/my-exams" class="nav-item">我的考试</router-link>
        </template>
        <template v-if="auth.role === 'teacher'">
          <router-link to="/classrooms" class="nav-item">空闲教室</router-link>
          <router-link to="/scores/input" class="nav-item">成绩录入</router-link>
          <router-link to="/advisor" class="nav-item">请假审批</router-link>
          <router-link to="/repairs" class="nav-item">报修中心</router-link>
          <router-link to="/my-invigilations" class="nav-item">监考安排</router-link>
        </template>
        <template v-if="auth.role === 'staff'">
          <router-link to="/classrooms" class="nav-item">空闲教室</router-link>
          <router-link to="/repairs/manage" class="nav-item">报修管理</router-link>
          <router-link to="/repairs" class="nav-item">报修中心</router-link>
        </template>
        <template v-if="auth.role === 'admin'">
          <router-link to="/admin" class="nav-item">管理后台</router-link>
          <router-link to="/advisor" class="nav-item">请假审批</router-link>
          <router-link to="/repairs/manage" class="nav-item">报修管理</router-link>
          <router-link to="/classrooms" class="nav-item">空闲教室</router-link>
          <router-link to="/repairs" class="nav-item">报修中心</router-link>
        </template>
      </div>
      <div class="nav-right">
        <el-popover placement="bottom" :width="360" trigger="click">
          <template #reference>
            <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99" class="bell-btn">
              <span style="font-size:20px;cursor:pointer">🔔</span>
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
        <router-link to="/profile">
          <el-tooltip :content="auth.name" placement="bottom">
            <div class="avatar">{{ auth.name.charAt(0) }}</div>
          </el-tooltip>
        </router-link>
        <router-link to="/profile" class="logout-btn" style="color:rgba(255,255,255,.7);text-decoration:none;font-size:13px">个人中心</router-link>
        <el-button text class="logout-btn" @click="handleLogout">退出</el-button>
      </div>
    </div>
    <div v-if="mobile && mobileOpen" class="mobile-menu">
      <router-link v-for="item in mobileItems" :key="item.path" :to="item.path" class="mobile-item" @click="mobileOpen=false">{{ item.label }}</router-link>
      <router-link to="/notifications" class="mobile-item" @click="mobileOpen=false">通知中心</router-link>
      <div class="mobile-item" @click="handleLogout">退出登录</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import router from '../router'
import { getNotifications, getUnreadCount, markAllRead as markAllReadApi } from '../api/notification'
import { ElMessage } from 'element-plus'

const auth = useAuthStore()
const unreadCount = ref(0)
const latestNotifications = ref([])
const mobile = ref(window.innerWidth <= 768)
const mobileOpen = ref(false)
let ws = null, pollTimer = null

const mobileItems = computed(() => {
  const role = auth.role
  const map = {
    student: [
      { path: '/schedule', label: '我的课表' }, { path: '/selection', label: '选课中心' },
      { path: '/leaves', label: '请假申请' }, { path: '/classrooms', label: '空闲教室' },
      { path: '/scores', label: '我的成绩' }, { path: '/plan', label: '培养方案' }, { path: '/repairs', label: '报修中心' },
    ],
    teacher: [
      { path: '/classrooms', label: '空闲教室' }, { path: '/scores/input', label: '成绩录入' },
      { path: '/advisor', label: '请假审批' }, { path: '/repairs', label: '报修中心' },
    ],
    staff: [
      { path: '/classrooms', label: '空闲教室' }, { path: '/repairs/manage', label: '报修管理' },
      { path: '/repairs', label: '报修中心' },
    ],
    admin: [
      { path: '/admin', label: '管理后台' }, { path: '/advisor', label: '请假审批' },
      { path: '/repairs/manage', label: '报修管理' }, { path: '/classrooms', label: '空闲教室' },
      { path: '/repairs', label: '报修中心' },
    ],
  }
  return map[role] || []
})

function handleLogout() { auth.logout(); router.push('/login') }
function goNotifications() { router.push('/notifications') }

async function loadNotifications() {
  try {
    const [unreadRes, listRes] = await Promise.all([
      getUnreadCount(),
      getNotifications(5, 0),
    ])
    unreadCount.value = typeof unreadRes === 'number' ? unreadRes : (unreadRes?.count ?? 0)
    latestNotifications.value = listRes.notifications || []
  } catch {}
}

async function markAllRead() {
  try { await markAllReadApi(); unreadCount.value = 0 } catch {}
}

function connectWS() {
  const token = localStorage.getItem('sms_token')
  if (!token) return
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${protocol}://${window.location.hostname}:8000/ws?token=${token}`)
  ws.onmessage = (e) => { try { const m = JSON.parse(e.data); if (m.type === 'notification') unreadCount.value++ } catch {} }
  ws.onclose = () => { setTimeout(connectWS, 5000) }
}

window.addEventListener('resize', () => { mobile.value = window.innerWidth <= 768 })

onMounted(() => { loadNotifications(); connectWS(); pollTimer = setInterval(loadNotifications, 30000) })
onUnmounted(() => { if (ws) ws.close(); if (pollTimer) clearInterval(pollTimer) })
</script>

<style scoped>
@import '../styles/global.css';
.navbar { background:#1E3A5F; color:#fff; }
.nav-inner { max-width:1200px; margin:0 auto; display:flex; align-items:center; height:56px; padding:0 24px; gap:32px; }
.nav-left { display:flex; align-items:center; gap:12px; }
.nav-brand { font-size:18px; font-weight:700; white-space:nowrap; }
.nav-center { display:flex; gap:4px; flex:1; }
.nav-item { color:rgba(255,255,255,.7); text-decoration:none; font-size:14px; padding:6px 12px; border-radius:4px; }
.nav-item:hover { color:#fff; background:rgba(255,255,255,.1); }
.nav-item.router-link-active { color:#fff; background:rgba(255,255,255,.15); border-bottom:3px solid #fff; border-radius:4px 4px 0 0; }
.nav-right { display:flex; align-items:center; gap:12px; }
.bell-btn { cursor:pointer; }
.avatar { width:32px; height:32px; border-radius:50%; background:rgba(255,255,255,.2); display:flex; align-items:center; justify-content:center; font-size:14px; color:#fff; cursor:default; }
.logout-btn { color:rgba(255,255,255,.7) !important; }
.logout-btn:hover { color:#fff !important; }
.hamburger { color:#fff !important; font-size:20px; }
.mobile-menu { background:#1E3A5F; padding:8px 16px 16px; }
.mobile-item { display:block; color:rgba(255,255,255,.85); padding:10px 8px; text-decoration:none; font-size:14px; border-bottom:1px solid rgba(255,255,255,.08); }
.notif-item { padding:8px 0; border-bottom:1px solid #f0f0f0; cursor:pointer; }
.notif-item:last-child { border-bottom:none; }
.notif-item:hover { background:#f9fafb; }
</style>
