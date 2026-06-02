import request from './index'

export function getPlans() {
  return request.get('/training-plan/plans')
}

export function createPlan(data) {
  return request.post('/training-plan/plans', data)
}

export function getPlanCourses(planId) {
  return request.get(`/training-plan/plans/${planId}/courses`)
}

export function addPlanCourse(data) {
  return request.post('/training-plan/courses', data)
}

export function deletePlanCourse(courseId) {
  return request.delete(`/training-plan/courses/${courseId}`)
}

export function getMyPlan() {
  return request.get('/training-plan/my')
}

export function auditStudent(studentId) {
  return request.post(`/graduation/audit/${studentId}`)
}

export function auditBatch(major, grade) {
  return request.post('/graduation/audit-batch', null, { params: { major, grade } })
}

export function getAudits(major, grade) {
  return request.get('/graduation/audits', { params: { major, grade } })
}

export function getMyAudit() {
  return request.get('/graduation/my')
}
