import request from './index'

export function generateExams(data) { return request.post('/exam/generate', data || { semester: '2024-2025-1' }) }
export function listExams() { return request.get('/exam/list') }
export function publishExam(id) { return request.put(`/exam/${id}/publish`) }
export function getMyExams() { return request.get('/exam/my-exams') }
export function getMyInvigilations() { return request.get('/exam/my-invigilations') }
