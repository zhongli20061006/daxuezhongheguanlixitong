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
</style>
