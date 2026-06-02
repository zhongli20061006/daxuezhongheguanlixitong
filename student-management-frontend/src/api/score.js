import request from './index'

export function manualScore(data) {
  return request.post('/scores/manual', data)
}

export function importScores(schedule_id, file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post(`/scores/import?schedule_id=${schedule_id}`, formData)
}

export function calculateTotal(schedule_id) {
  return request.post(`/scores/calculate-total?schedule_id=${schedule_id}`)
}

export function updateScore(id, new_score) {
  return request.put(`/scores/${id}`, null, { params: { new_score } })
}

export function getStudentScores(student_id) {
  return request.get(`/scores/student/${student_id}`)
}

export function getScoresBySchedule(schedule_id, score_type) {
  return request.get(`/scores/by-schedule/${schedule_id}`, { params: { score_type } })
}
