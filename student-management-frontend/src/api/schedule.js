import request from './index'

export function getMySchedule() {
  return request.get('/schedule/my')
}

export function getClassSchedule(class_id) {
  return request.get(`/schedule/class/${class_id}`)
}

export function createSchedule(data) {
  return request.post('/schedule', data)
}

export function updateSchedule(id, data) {
  return request.put(`/schedule/${id}`, data)
}

export function deleteSchedule(id) {
  return request.delete(`/schedule/${id}`)
}
