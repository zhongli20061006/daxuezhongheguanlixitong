import request from './index'

export function setSelectionWindow(data) {
  return request.post('/admin/selection-window', data)
}

export function getSelectionWindow() {
  return request.get('/admin/selection-window')
}

export function updateCapacity(schedule_id, capacity) {
  return request.put(`/admin/capacity/${schedule_id}`, { capacity })
}

export function getUsers() {
  return request.get('/admin/users')
}

export function resetPassword(user_id, new_password) {
  return request.post(`/admin/reset-password/${user_id}`, { new_password })
}
