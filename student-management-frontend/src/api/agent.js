import request from './index'

export function sendChat(sessionId, message) {
  return request.post('/agent/chat', { session_id: sessionId || null, message })
}

export function confirmAction(token) {
  return request.post('/agent/confirm', { token })
}

export function getAgentStatus() {
  return request.get('/agent/status')
}

export function listSessions() {
  return request.get('/agent/sessions')
}

export function getSessionMessages(sessionId) {
  return request.get(`/agent/sessions/${sessionId}`)
}

export function deleteSession(sessionId) {
  return request.delete(`/agent/sessions/${sessionId}`)
}
