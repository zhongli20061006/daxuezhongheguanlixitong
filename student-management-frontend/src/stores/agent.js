import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  confirmAction, deleteSession, getAgentStatus, getSessionMessages, listSessions, sendChat,
} from '../api/agent'

export const useAgentStore = defineStore('agent', () => {
  const sessions = ref([])
  const currentSessionId = ref('')
  const messages = ref([])
  const sessionCache = ref({})  // session_id -> messages[]（按会话保存，切换/新建不丢）
  const sending = ref(false)
  const loadingHistory = ref(false)
  const ollamaStatus = ref('unknown')

  async function loadSessions() {
    const res = await listSessions()
    sessions.value = res.sessions || []
  }

  function newSession() {
    // 只是把当前视图切到一个新的空对话；旧会话仍留在左侧列表，可随时切回
    cacheCurrent()
    currentSessionId.value = ''
    messages.value = []
  }

  function cacheCurrent() {
    if (currentSessionId.value) {
      sessionCache.value[currentSessionId.value] = messages.value.map(m => ({ ...m }))
    }
  }

  async function send(text) {
    if (!text.trim() || sending.value) return
    sending.value = true
    messages.value.push({ kind: 'text', content: text, own: true })
    try {
      const res = await sendChat(currentSessionId.value, text.trim())
      if (res.session_id && res.session_id !== currentSessionId.value) {
        // 首次发送会在后端创建新会话：先把旧会话缓存好，再切到新会话
        cacheCurrent()
        currentSessionId.value = res.session_id
      }
      messages.value.push(...(res.messages || []).map(m => ({ ...m, own: false })))
      cacheCurrent()
      await loadSessions()
    } catch {
      messages.value.push({ kind: 'error', content: '请求失败，请检查后端服务', own: false })
    } finally {
      sending.value = false
    }
  }

  async function selectSession(id) {
    if (id === currentSessionId.value) return
    cacheCurrent()
    currentSessionId.value = id
    if (sessionCache.value[id]) {
      messages.value = sessionCache.value[id].map(m => ({ ...m }))
      return
    }
    loadingHistory.value = true
    messages.value = []
    try {
      const res = await getSessionMessages(id)
      messages.value = (res.messages || []).map(m => ({
        kind: m.kind || 'text',
        content: m.content,
        own: m.role === 'user',
      }))
      sessionCache.value[id] = messages.value.map(m => ({ ...m }))
    } catch {
      messages.value = [{ kind: 'error', content: '会话加载失败或已过期，请新建对话', own: false }]
    } finally {
      loadingHistory.value = false
    }
  }

  async function confirm(token) {
    sending.value = true
    try {
      const res = await confirmAction(token)
      messages.value.push(...(res.messages || []).map(m => ({ ...m, own: false })))
      cacheCurrent()
    } catch {
      messages.value.push({ kind: 'error', content: '确认失败，请重试', own: false })
    } finally {
      sending.value = false
    }
  }

  async function removeSession(id) {
    await deleteSession(id)
    delete sessionCache.value[id]
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

  function reset() {
    // 切换账号时清空，避免看到上一个账号的会话与消息
    sessions.value = []
    currentSessionId.value = ''
    messages.value = []
    sessionCache.value = {}
    sending.value = false
    loadingHistory.value = false
    ollamaStatus.value = 'unknown'
  }

  return {
    sessions, currentSessionId, messages, sessionCache, sending, loadingHistory, ollamaStatus,
    loadSessions, newSession, send, selectSession, confirm, removeSession, refreshStatus, reset,
  }
})
