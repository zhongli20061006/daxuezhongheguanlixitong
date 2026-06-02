<template>
  <div class="login-wrapper">
    <div class="login-brand">
      <div class="brand-content">
        <div class="brand-logo">🎓</div>
        <h1 class="brand-title">大学生管理系统</h1>
        <p class="brand-subtitle">统一的校园服务入口</p>
      </div>
    </div>
    <div class="login-form">
      <div class="form-card">
        <p class="form-greeting">欢迎登录</p>
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
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function handleLogin() {
  if (!username.value || !password.value) { errorMsg.value = '请输入用户名和密码'; return }
  loading.value = true; errorMsg.value = ''
  try {
    const res = await authStore.login(username.value, password.value)
    if (res.must_change_password) {
      router.push('/change-password')
    } else {
      const defaults = { student: '/schedule', teacher: '/scores/input', staff: '/repairs/manage', admin: '/admin' }
      router.push(defaults[res.role] || '/')
    }
  } catch {
    errorMsg.value = '用户名或密码错误'
  } finally {
    loading.value = false
  }
}

function forgetPwd() {
  ElMessageBox.alert('请联系管理员重置密码', '提示')
}
</script>

<style scoped>
.login-wrapper { display:flex; min-height:100vh; }
.login-brand { flex:0 0 40%; background:linear-gradient(135deg,#1E3A5F 0%,#2563EB 100%); display:flex; align-items:center; justify-content:center; }
.brand-content { text-align:center; padding:40px; }
.brand-logo { font-size:64px; margin-bottom:16px; }
.brand-title { color:#fff; font-size:28px; font-weight:700; margin:0 0 8px; }
.brand-subtitle { color:rgba(255,255,255,.7); font-size:14px; margin:0; }
.login-form { flex:1; display:flex; align-items:center; justify-content:center; background:#F3F4F6; }
.form-card { width:100%; max-width:380px; padding:32px; }
.form-greeting { font-size:14px; color:#6B7280; margin:0 0 24px; }
.login-btn { width:100%; height:44px; font-size:16px; }
.forgot-pwd { text-align:center; color:#9CA3AF; font-size:13px; cursor:pointer; margin-top:12px; }
.forgot-pwd:hover { color:#2563EB; }
@media (max-width:768px) {
  .login-wrapper { flex-direction:column; }
  .login-brand { flex:0 0 160px; }
  .brand-logo { font-size:40px; }
  .brand-title { font-size:22px; }
}
</style>
