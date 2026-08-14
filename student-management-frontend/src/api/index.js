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
      // 跳过 /auth/me、/auth/logout、/auth/login，这些端点的 401 属于正常业务状态
      // （未登录、退出登录、用户名或密码错误），不应误报为"登录已过期"
      if (url.includes('/auth/me') || url.includes('/auth/logout') || url.includes('/auth/login')) {
        return Promise.reject(error)
      }
      // 动态导入避免 api/auth ↔ api/index 模块级循环依赖；同时清内存态与 localStorage
      import('../stores/auth')
        .then(({ useAuthStore }) => { useAuthStore().clearSession() })
        .catch(() => {})
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
