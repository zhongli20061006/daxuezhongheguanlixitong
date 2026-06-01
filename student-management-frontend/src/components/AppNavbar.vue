<template>
  <el-menu mode="horizontal" :ellipsis="false" router class="navbar">
    <el-menu-item index="/" disabled class="brand">
      <span style="font-weight:bold;font-size:16px">大学生管理系统</span>
    </el-menu-item>
    <div class="flex-grow" />
    <template v-if="auth.role === 'student'">
      <el-menu-item index="/schedule">我的课表</el-menu-item>
      <el-menu-item index="/selection">选课中心</el-menu-item>
      <el-menu-item index="/leaves">请假申请</el-menu-item>
      <el-menu-item index="/classrooms">空闲教室</el-menu-item>
      <el-menu-item index="/scores">我的成绩</el-menu-item>
      <el-menu-item index="/repairs">报修中心</el-menu-item>
    </template>
    <template v-if="auth.role === 'teacher'">
      <el-menu-item index="/classrooms">空闲教室</el-menu-item>
      <el-menu-item index="/scores/input">成绩录入</el-menu-item>
      <el-menu-item index="/advisor">请假审批</el-menu-item>
      <el-menu-item index="/repairs">报修中心</el-menu-item>
    </template>
    <template v-if="auth.role === 'staff'">
      <el-menu-item index="/classrooms">空闲教室</el-menu-item>
      <el-menu-item index="/repairs/manage">报修管理</el-menu-item>
      <el-menu-item index="/repairs">报修中心</el-menu-item>
    </template>
    <template v-if="auth.role === 'admin'">
      <el-menu-item index="/admin">管理后台</el-menu-item>
      <el-menu-item index="/advisor">请假审批</el-menu-item>
      <el-menu-item index="/repairs/manage">报修管理</el-menu-item>
      <el-menu-item index="/classrooms">空闲教室</el-menu-item>
      <el-menu-item index="/repairs">报修中心</el-menu-item>
    </template>
    <div class="flex-grow" />
    <el-menu-item index="/notifications">
      <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99">
        <span>通知</span>
      </el-badge>
    </el-menu-item>
    <el-menu-item disabled>{{ auth.name }}</el-menu-item>
    <el-menu-item @click="handleLogout">退出</el-menu-item>
  </el-menu>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import router from '../router'
import { getUnreadCount } from '../api/notification'

const auth = useAuthStore()
const unreadCount = ref(0)
let ws = null
let pollTimer = null

function handleLogout() {
  auth.logout()
  router.push('/login')
}

function connectWS() {
  const token = localStorage.getItem('sms_token')
  if (!token) return
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const host = window.location.hostname
  ws = new WebSocket(`${protocol}://${host}:8000/ws?token=${token}`)
  ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data)
      if (msg.type === 'notification') {
        unreadCount.value++
      }
    } catch {}
  }
  ws.onclose = () => {
    setTimeout(connectWS, 5000)
  }
}

async function loadUnreadCount() {
  try {
    const res = await getUnreadCount()
    unreadCount.value = res.count
  } catch {}
}

onMounted(() => {
  loadUnreadCount()
  connectWS()
  pollTimer = setInterval(loadUnreadCount, 30000)
})

onUnmounted(() => {
  if (ws) ws.close()
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.navbar { padding: 0 20px; border-bottom: 1px solid #e6e6e6; }
.flex-grow { flex-grow: 1; }
.brand { cursor: default !important; }
.brand:hover { background: transparent !important; }
</style>
