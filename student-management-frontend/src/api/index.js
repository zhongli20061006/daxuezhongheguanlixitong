import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'
import { logout as logoutApi } from './auth'

const baseURL = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const request = axios.create({
  baseURL,
  timeout: 15000
})

// 请求拦截器：自动注入 Bearer token（内存存储，防 XSS）
request.interceptors.request.use(config => {
  const token = localStorage.getItem('sms_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一错误处理
request.interceptors.response.use(
  response => response.data,
  error => {
    const status = error.response?.status
    const detail = error.response?.data?.detail || '请求失败'
    const url = error.config?.url || ''
    if (status === 401) {
      // 跳过 /auth/me 和 /auth/logout，这些端点预期可能 401（未登录时的正常状态）
      if (url.includes('/auth/me') || url.includes('/auth/logout')) {
        return Promise.reject(error)
      }
      localStorage.removeItem('sms_token')
      localStorage.removeItem('sms_role')
      localStorage.removeItem('sms_name')
      localStorage.removeItem('sms_user_id')
      localStorage.removeItem('sms_must_change')
      logoutApi().catch(() => {})
      ElMessage.error('登录已过期，请重新登录')
      router.push('/login')
    } else {
      ElMessage.error(detail)
    }
    return Promise.reject(error)
  }
)

export default request