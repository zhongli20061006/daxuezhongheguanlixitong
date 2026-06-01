import request from './index'

export function createRepair(data) {
  return request.post('/repairs', data)
}

export function getRepairs(params = {}) {
  return request.get('/repairs', { params })
}

export function updateRepairStatus(id, status) {
  return request.put(`/repairs/${id}/status`, { status })
}
