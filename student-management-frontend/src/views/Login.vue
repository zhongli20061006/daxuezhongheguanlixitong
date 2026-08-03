<template>
  <div class="login-wrapper">
    <div class="login-brand">
      <div class="brand-pattern"></div>
      <div class="brand-dot dot-1"></div>
      <div class="brand-dot dot-2"></div>
      <div class="brand-dot dot-3"></div>
      <div class="brand-content">
        <div class="brand-logo">🎓</div>
        <h1 class="brand-title">智伴校园</h1>
        <p class="brand-subtitle">统一的校园服务入口</p>
      </div>
    </div>
    <div class="login-form">
      <div class="form-card">
        <div class="form-card-accent"></div>
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
        <p class="login-footer">© 2024 智伴校园</p>
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
      const defaults = { student: '/', teacher: '/', staff: '/', admin: '/' }
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
.login-brand {
  flex:0 0 40%;
  background:linear-gradient(135deg,#0F172A 0%,#1E3A5F 40%,#1E40AF 100%);
  display:flex;
  align-items:center;
  justify-content:center;
  position:relative;
  overflow:hidden;
}
.brand-pattern {
  position:absolute;
  inset:0;
  background-image:
    radial-gradient(circle at 20% 30%,rgba(255,255,255,0.06) 0%,transparent 50%),
    radial-gradient(circle at 80% 70%,rgba(255,255,255,0.04) 0%,transparent 50%),
    radial-gradient(circle at 50% 50%,rgba(255,255,255,0.03) 0%,transparent 70%);
  pointer-events:none;
}
.brand-dot {
  position:absolute;
  border-radius:50%;
  background:rgba(255,255,255,0.06);
  pointer-events:none;
}
.brand-dot.dot-1 { width:120px;height:120px;top:-30px;right:-20px; }
.brand-dot.dot-2 { width:200px;height:200px;bottom:-60px;left:-60px; }
.brand-dot.dot-3 { width:80px;height:80px;top:50%;left:15%;transform:translateY(-50%); }
.brand-content { text-align:center; padding:40px; position:relative; z-index:1; }
.brand-logo { font-size:72px; margin-bottom:16px; }
.brand-title { color:#fff; font-size:28px; font-weight:700; margin:0 0 8px; text-shadow:0 2px 12px rgba(0,0,0,0.3); }
.brand-subtitle { color:rgba(255,255,255,.7); font-size:14px; margin:0; }
.login-form { flex:1; display:flex; align-items:center; justify-content:center; background:linear-gradient(180deg,#F8FAFC 0%,#F0F2F5 100%); }
.form-card {
  width:100%; max-width:380px; padding:32px;
  background:#fff;
  border-radius:var(--radius-xl);
  box-shadow:var(--shadow-xl);
  position:relative;
  animation:scaleIn 0.3s ease-out;
}
.form-card-accent {
  position:absolute;
  top:0; left:24px; right:24px;
  height:3px;
  background:linear-gradient(90deg,#2563EB,#1D4ED8,#60A5FA);
  border-radius:0 0 3px 3px;
}
.form-greeting { font-size:14px; color:#6B7280; margin:0 0 24px; }
.login-btn {
  width:100%; height:48px; font-size:16px;
  background:linear-gradient(135deg,#2563EB,#1D4ED8) !important;
  border:none !important;
}
.login-btn:hover {
  box-shadow:0 6px 20px rgba(37,99,235,0.45) !important;
  transform:translateY(-1px);
}
.forgot-pwd { text-align:center; color:#9CA3AF; font-size:13px; cursor:pointer; margin-top:12px; }
.forgot-pwd:hover { color:#2563EB; }
.login-footer { text-align:center; color:#D1D5DB; font-size:11px; margin-top:16px; }
:deep(.el-input__wrapper) { transition:box-shadow var(--transition-base),border-color var(--transition-base); }
:deep(.el-input__wrapper.is-focus) { box-shadow:0 0 0 1px var(--color-primary) inset,0 0 0 3px rgba(37,99,235,0.15) !important; }
@media (max-width:768px) {
  .login-wrapper { flex-direction:column; }
  .login-brand { flex:0 0 160px; }
  .brand-logo { font-size:40px; }
  .brand-title { font-size:22px; }
  .brand-dot { display:none; }
}
</style>
