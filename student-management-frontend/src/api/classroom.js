import request from './index'

export function getAvailableClassrooms(params) {
  return request.get('/classrooms/available', { params })
}

export function getClassroomAvailability(id, params) {
  return request.get(`/classrooms/${id}/availability`, { params })
}
