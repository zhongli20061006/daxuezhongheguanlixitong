<template>
  <div class="login-wrapper">
    <el-card class="login-card">
      <h2 style="text-align:center;margin-bottom:20px">大学生管理系统</h2>
      <el-form @submit.prevent="handleLogin">
        <el-form-item>
          <el-input v-model="username" placeholder="学号或工号" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="password" type="password" show-password placeholder="密码" size="large" />
        </el-form-item>
        <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon closable @close="errorMsg=''" style="margin-bottom:12px" />
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" @click="handleLogin" style="width:100%">
            {{ loading ? '登录中...' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>
      <p style="text-align:center;color:#999;cursor:pointer" @click="forgetPwd">忘记密码?</p>
    </el-card>
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
  } catch (e) {
    errorMsg.value = e?.response?.data?.detail || '用户名或密码错误'
  } finally {
    loading.value = false
  }
}

function forgetPwd() {
  ElMessageBox.alert('请联系管理员重置密码', '提示')
}
</script>

<style scoped>
.login-wrapper { display:flex; justify-content:center; align-items:center; height:100vh; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.login-card { width:400px; padding:10px 20px; }
</style>
