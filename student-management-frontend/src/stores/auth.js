import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, changePassword as changePwdApi, getMe as getMeApi, logout as logoutApi } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref('')  // 仅用于 WebSocket，不持久化
  const role = ref('')
  const name = ref('')
  const userId = ref('')
  const mustChangePassword = ref(false)

  const isLoggedIn = computed(() => !!role.value)
  const isAdmin = computed(() => role.value === 'admin')

  async function checkAuth() {
    try {
      const res = await getMeApi()
      role.value = res.role || ''
      name.value = res.username || ''
      userId.value = res.username || ''
      mustChangePassword.value = !!res.must_change_password
      return true
    } catch {
      role.value = ''
      name.value = ''
      userId.value = ''
      mustChangePassword.value = false
      return false
    }
  }

  function restoreSession() {
    // 跨域场景：从 localStorage 恢复登录态（cookie 在跨域下不可用）
    token.value = localStorage.getItem('sms_token') || ''
    role.value = localStorage.getItem('sms_role') || ''
    name.value = localStorage.getItem('sms_name') || ''
    userId.value = localStorage.getItem('sms_user_id') || ''
    mustChangePassword.value = localStorage.getItem('sms_must_change') === 'true'
  }

  async function login(username, password) {
    const res = await loginApi(username, password)
    token.value = res.access_token
    // 跨域场景：token 仍需存 localStorage 供 axios 拦截器注入 Authorization header
    // httpOnly cookie 作为同域部署时的补充（当前跨域不可用）
    localStorage.setItem('sms_token', res.access_token)
    localStorage.setItem('sms_role', res.role)
    localStorage.setItem('sms_name', username)
    localStorage.setItem('sms_user_id', username)
    localStorage.setItem('sms_must_change', String(!!res.must_change_password))
    role.value = res.role
    mustChangePassword.value = res.must_change_password
    name.value = username
    userId.value = username
    return res
  }

  async function changePassword(oldPwd, newPwd) {
    await changePwdApi(oldPwd, newPwd)
    mustChangePassword.value = false
    localStorage.setItem('sms_must_change', 'false')
  }

  async function logout() {
    try {
      await logoutApi()
    } catch { /* ignore */ }
    token.value = ''
    role.value = ''
    name.value = ''
    userId.value = ''
    mustChangePassword.value = false
    localStorage.removeItem('sms_token')
    localStorage.removeItem('sms_role')
    localStorage.removeItem('sms_name')
    localStorage.removeItem('sms_user_id')
    localStorage.removeItem('sms_must_change')
  }

  return { token, role, name, userId, mustChangePassword, isLoggedIn, isAdmin, login, changePassword, logout, restoreSession, checkAuth }
})