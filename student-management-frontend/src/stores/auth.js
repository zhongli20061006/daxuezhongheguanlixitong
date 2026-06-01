import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, changePassword as changePwdApi } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref('')
  const role = ref('')
  const name = ref('')
  const userId = ref('')
  const mustChangePassword = ref(false)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => role.value === 'admin')

  function persist() {
    localStorage.setItem('sms_token', token.value)
    localStorage.setItem('sms_role', role.value)
    localStorage.setItem('sms_name', name.value)
    localStorage.setItem('sms_user_id', userId.value)
    localStorage.setItem('sms_must_change', mustChangePassword.value.toString())
  }

  function restoreSession() {
    token.value = localStorage.getItem('sms_token') || ''
    role.value = localStorage.getItem('sms_role') || ''
    name.value = localStorage.getItem('sms_name') || ''
    userId.value = localStorage.getItem('sms_user_id') || ''
    mustChangePassword.value = localStorage.getItem('sms_must_change') === 'true'
  }

  async function login(username, password) {
    const res = await loginApi(username, password)
    token.value = res.access_token
    role.value = res.role
    mustChangePassword.value = res.must_change_password
    name.value = username
    userId.value = username
    persist()
    return res
  }

  async function changePassword(oldPwd, newPwd) {
    await changePwdApi(oldPwd, newPwd)
    mustChangePassword.value = false
    persist()
  }

  function logout() {
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

  return { token, role, name, userId, mustChangePassword, isLoggedIn, isAdmin, login, changePassword, logout, restoreSession, persist }
})
