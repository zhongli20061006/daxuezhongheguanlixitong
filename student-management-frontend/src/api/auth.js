import request from './index'

export function login(username, password) {
  return request.post('/auth/login', { username, password })
}

export function logout() {
  return request.post('/auth/logout')
}

export function getMe() {
  return request.get('/auth/me')
}

export function changePassword(old_password, new_password) {
  return request.post('/auth/change-password', { old_password, new_password })
}
