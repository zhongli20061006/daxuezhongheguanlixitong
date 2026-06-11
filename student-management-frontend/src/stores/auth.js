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
    return checkAuth()
  }

  async function login(username, password) {
    const res = await loginApi(username, password)
    token.value = res.access_token  // 保留 token 用于 WebSocket
    role.value = res.role
    mustChangePassword.value = res.must_change_password
    name.value = username
    userId.value = username
    return res
  }

  async function changePassword(oldPwd, newPwd) {
    await changePwdApi(oldPwd, newPwd)
    mustChangePassword.value = false
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
  }

  return { token, role, name, userId, mustChangePassword, isLoggedIn, isAdmin, login, changePassword, logout, restoreSession, checkAuth }
})