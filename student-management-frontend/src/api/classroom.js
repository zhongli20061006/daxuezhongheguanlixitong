import request from './index'

export function getAvailableClassrooms(params) {
  return request.get('/classrooms/available', { params })
}

export function getClassroomAvailability(id, params) {
  return request.get(`/classrooms/${id}/availability`, { params })
}

export function reserveClassroom(params) {
  return request.post('/classrooms/reserve', null, { params })
}

export function getMyReservations() {
  return request.get('/classrooms/my-reservations')
}

export function cancelReservation(id) {
  return request.put(`/classrooms/reservation/${id}/cancel`)
}
