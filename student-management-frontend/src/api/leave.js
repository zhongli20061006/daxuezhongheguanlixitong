import api from './index'

export function applyLeave(data) {
  return api.post('/leave/apply', data)
}

export function getMyLeaves() {
  return api.get('/leave/my')
}

export function cancelLeave(id) {
  return api.post(`/leave/${id}/cancel`)
}

export function getLeaveDetail(id) {
  return api.get(`/leave/${id}/detail`)
}

export function getPendingApprovals() {
  return api.get('/advisor/pending-approvals')
}

export function approveLeave(data) {
  return api.post('/advisor/approve', data)
}
