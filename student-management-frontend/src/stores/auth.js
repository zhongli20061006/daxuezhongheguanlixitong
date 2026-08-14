import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, changePassword as changePwdApi, getMe as getMeApi, logout as logoutApi } from '../api/auth'
import { useAgentStore } from './agent'

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
      name.value = res.name || res.username || ''
      userId.value = res.username || ''
      mustChangePassword.value = !!res.must_change_password
      // 恢复 token（供 WS/请求头使用，服务端校验通过才保留）
      if (!token.value) token.value = localStorage.getItem('sms_token') || ''
      return true
    } catch {
      clearSession()
      return false
    }
  }

  function clearSession() {
    // 纯本地清态（不调用任何 API），供 401 拦截器与 logout 复用
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

  function restoreSession() {
    // 仅用于恢复本地 token（跨域场景下 /auth/me 走 Authorization header）
    // 角色等敏感状态必须随后经 checkAuth() 由服务端确认，不可直接信任本地值
    token.value = localStorage.getItem('sms_token') || ''
  }

  async function login(username, password) {
    const res = await loginApi(username, password)
    token.value = res.access_token
    // 跨域场景：token 仍需存 localStorage 供 axios 拦截器注入 Authorization header
    // httpOnly cookie 作为同域部署时的补充（当前跨域不可用）
    localStorage.setItem('sms_token', res.access_token)
    localStorage.setItem('sms_role', res.role)
    localStorage.setItem('sms_name', res.name || username)
    localStorage.setItem('sms_user_id', username)
    localStorage.setItem('sms_must_change', String(!!res.must_change_password))
    role.value = res.role
    mustChangePassword.value = res.must_change_password
    name.value = res.name || username
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
    clearSession()
    // 清空智能体会话状态，避免下一个账号看到上一个账号的对话
    useAgentStore().reset()
  }

  return { token, role, name, userId, mustChangePassword, isLoggedIn, isAdmin, login, changePassword, logout, restoreSession, checkAuth, clearSession }
})
