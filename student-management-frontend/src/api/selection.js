import request from './index'

export function enroll(schedule_id) {
  return request.post(`/selection/enroll?schedule_id=${schedule_id}`)
}

export function drop(schedule_id) {
  return request.post(`/selection/drop?schedule_id=${schedule_id}`)
}

export function getMyCourses() {
  return request.get('/selection/my-courses')
}

export function getAvailableCourses() {
  return request.get('/selection/available-courses')
}
