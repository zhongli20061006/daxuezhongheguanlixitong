import { defineStore } from 'pinia'
import { ref } from 'vue'
import { confirmAction, deleteSession, getAgentStatus, listSessions, sendChat } from '../api/agent'

export const useAgentStore = defineStore('agent', () => {
  const sessions = ref([])
  const currentSessionId = ref('')
  const messages = ref([])
  const sending = ref(false)
  const ollamaStatus = ref('unknown')

  async function loadSessions() {
    const res = await listSessions()
    sessions.value = res.sessions || []
  }

  async function newSession() {
    currentSessionId.value = ''
    messages.value = []
    await loadSessions()
  }

  async function send(text) {
    if (!text.trim() || sending.value) return
    sending.value = true
    messages.value.push({ kind: 'text', content: text, own: true })
    try {
      const res = await sendChat(currentSessionId.value, text.trim())
      currentSessionId.value = res.session_id
      messages.value.push(...(res.messages || []).map(m => ({ ...m, own: false })))
      await loadSessions()
    } catch {
      messages.value.push({ kind: 'error', content: '请求失败，请检查后端服务', own: false })
    } finally {
      sending.value = false
    }
  }

  async function confirm(token) {
    sending.value = true
    try {
      const res = await confirmAction(token)
      messages.value.push(...(res.messages || []).map(m => ({ ...m, own: false })))
    } catch {
      messages.value.push({ kind: 'error', content: '确认失败，请重试', own: false })
    } finally {
      sending.value = false
    }
  }

  async function removeSession(id) {
    await deleteSession(id)
    if (currentSessionId.value === id) {
      currentSessionId.value = ''
      messages.value = []
    }
    await loadSessions()
  }

  async function refreshStatus() {
    try {
      const res = await getAgentStatus()
      ollamaStatus.value = res.ollama
    } catch {
      ollamaStatus.value = 'unknown'
    }
  }

  return {
    sessions, currentSessionId, messages, sending, ollamaStatus,
    loadSessions, newSession, send, confirm, removeSession, refreshStatus,
  }
})
