import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const baseURL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? 'http://localhost:8000'
  : `http://${window.location.hostname}:8000`

const request = axios.create({
  baseURL,
  timeout: 15000
})

// 请求拦截器：自动注入 token
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
    if (status === 401) {
      localStorage.removeItem('sms_token')
      localStorage.removeItem('sms_role')
      localStorage.removeItem('sms_name')
      localStorage.removeItem('sms_user_id')
      localStorage.removeItem('sms_must_change')
      ElMessage.error('登录已过期，请重新登录')
      router.push('/login')
    } else {
      ElMessage.error(detail)
    }
    return Promise.reject(error)
  }
)

export default request
