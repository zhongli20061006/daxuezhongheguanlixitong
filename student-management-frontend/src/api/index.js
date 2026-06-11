import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'
import { logout as logoutApi } from './auth'

const baseURL = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const request = axios.create({
  baseURL,
  timeout: 15000
})

// 响应拦截器：统一错误处理
request.interceptors.response.use(
  response => response.data,
  error => {
    const status = error.response?.status
    const detail = error.response?.data?.detail || '请求失败'
    if (status === 401) {
      // 调用退出接口清除 cookie，然后跳转登录页
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