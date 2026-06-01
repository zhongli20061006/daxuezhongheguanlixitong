<template>
  <div class="pwd-wrapper">
    <el-card class="pwd-card">
      <h2 style="text-align:center;margin-bottom:20px">修改密码</h2>
      <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon closable @close="errorMsg=''" style="margin-bottom:12px" />
      <el-form>
        <el-form-item>
          <el-input v-model="oldPwd" type="password" show-password placeholder="旧密码" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="newPwd" type="password" show-password placeholder="新密码（至少6位）" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="confirmPwd" type="password" show-password placeholder="确认新密码" size="large" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" @click="handleChange" style="width:100%">
            {{ loading ? '提交中...' : '确认修改' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const oldPwd = ref('')
const newPwd = ref('')
const confirmPwd = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function handleChange() {
  if (newPwd.value.length < 6) { errorMsg.value = '新密码至少6位'; return }
  if (newPwd.value !== confirmPwd.value) { errorMsg.value = '两次输入不一致'; return }
  if (oldPwd.value === newPwd.value) { errorMsg.value = '新密码不能与旧密码相同'; return }
  loading.value = true; errorMsg.value = ''
  try {
    await authStore.changePassword(oldPwd.value, newPwd.value)
    const defaults = { student: '/schedule', teacher: '/scores/input', staff: '/repairs/manage', admin: '/admin' }
    router.push(defaults[authStore.role] || '/')
  } catch (e) {
    errorMsg.value = e?.response?.data?.detail || '旧密码不正确'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.pwd-wrapper { display:flex; justify-content:center; align-items:center; height:100vh; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.pwd-card { width:400px; padding:10px 20px; }
</style>
