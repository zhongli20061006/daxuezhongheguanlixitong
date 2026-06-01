import request from './index'

export function login(username, password) {
  return request.post('/auth/login', { username, password })
}

export function changePassword(old_password, new_password) {
  return request.post('/auth/change-password', { old_password, new_password })
}
