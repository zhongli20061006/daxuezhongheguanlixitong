import api from './index'

export function getNotifications(limit = 50, offset = 0) {
  return api.get('/notification/list', { params: { limit, offset } })
}

export function getUnreadCount() {
  return api.get('/notification/unread-count')
}

export function markAsRead(id) {
  return api.post(`/notification/${id}/read`)
}

export function markAllRead() {
  return api.post('/notification/read-all')
}

export function deleteNotification(id) {
  return api.delete(`/notification/${id}`)
}

export function cleanupRead(days = 7) {
  return api.post('/notification/cleanup', null, { params: { days } })
}
