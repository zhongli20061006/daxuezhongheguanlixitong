<template>
  <div class="agent-layout">
    <aside class="session-panel">
      <el-button type="primary" class="new-session-btn" @click="store.newSession()">
        新建对话
      </el-button>
      <div class="session-list">
        <div
          v-for="s in store.sessions"
          :key="s.session_id"
          class="session-item"
          :class="{ active: s.session_id === store.currentSessionId }"
          @click="store.selectSession(s.session_id)"
        >
          <span class="session-title">{{ sessionTitle(s) }}</span>
          <el-button link type="danger" size="small" @click.stop="store.removeSession(s.session_id)">
            删除
          </el-button>
        </div>
      </div>
    </aside>

    <main class="chat-panel">
      <header class="chat-header">
        <h2>智能体助手</h2>
        <span class="model-status" :class="store.ollamaStatus">
          {{ store.ollamaStatus === 'ok' ? '本地模型在线' : '本地模型未连接' }}
        </span>
      </header>

      <div ref="listRef" class="message-list">
        <div v-if="store.loadingHistory" class="msg typing">会话加载中…</div>
        <template v-for="(m, idx) in store.messages" :key="idx">
          <div v-if="m.own" class="msg own">{{ m.content }}</div>
          <div v-else-if="m.kind === 'text'" class="msg">{{ m.content }}</div>
          <div v-else-if="m.kind === 'error'" class="msg error">{{ m.content }}</div>
          <div v-else-if="m.kind === 'summary'" class="msg summary">{{ m.content }}</div>
          <el-card v-else-if="m.kind === 'card'" class="msg-card">
            <template #header>
              <div class="card-head">
                <span>{{ m.title }}</span>
                <el-button v-if="m.navigation" link type="primary" @click="go(m.navigation)">
                  前往页面
                </el-button>
              </div>
            </template>
            <div class="card-content">
              <div v-if="isPlan(m)" class="plan-box">
                <p class="plan-summary">{{ planOf(m).summary }}</p>
                <div v-for="c in planOf(m).courses" :key="c.course" class="plan-item">
                  <div class="plan-item-head">
                    <strong>{{ c.course }}</strong>
                    <el-tag size="small" :type="priorityType(c.priority)">{{ c.priority }}优先</el-tag>
                    <span class="plan-duration">{{ c.duration_minutes }}分钟</span>
                  </div>
                  <p class="plan-line"><span class="plan-label">课前</span>{{ c.preview }}</p>
                  <p class="plan-line"><span class="plan-label">课后</span>{{ c.review }}</p>
                </div>
              </div>
              <el-table v-else-if="m.data?.courses" :data="m.data.courses" size="small">
                <el-table-column prop="course" label="课程" />
                <el-table-column prop="period" label="节次" width="80" />
                <el-table-column prop="classroom" label="教室" width="100" />
                <el-table-column prop="teacher" label="老师" width="100" />
              </el-table>
              <el-table v-else-if="m.data?.scores" :data="m.data.scores" size="small">
                <el-table-column prop="course" label="课程" />
                <el-table-column prop="score" label="分数" width="70" />
                <el-table-column prop="gpa" label="绩点" width="70" />
                <el-table-column prop="type" label="类型" width="80" />
              </el-table>
              <el-table v-else-if="m.data?.notifications" :data="m.data.notifications" size="small">
                <el-table-column prop="title" label="标题" />
                <el-table-column prop="content" label="内容" />
              </el-table>
              <el-table v-else-if="m.data?.exams" :data="m.data.exams" size="small">
                <el-table-column prop="subject" label="科目" />
                <el-table-column prop="date" label="日期" width="100" />
                <el-table-column prop="time" label="时间" width="120" />
                <el-table-column prop="classroom" label="教室" width="100" />
                <el-table-column prop="seat" label="座位" width="70" />
              </el-table>
              <el-table v-else-if="m.data?.classrooms" :data="m.data.classrooms" size="small">
                <el-table-column prop="name" label="教室" />
                <el-table-column prop="building" label="教学楼" width="110" />
                <el-table-column prop="capacity" label="容量" width="70" />
                <el-table-column label="投影" width="70">
                  <template #default="{ row }">{{ row.has_projector ? '有' : '无' }}</template>
                </el-table-column>
              </el-table>
              <pre v-else class="plain">{{ m.content }}</pre>
            </div>
          </el-card>
          <el-card v-else-if="m.kind === 'confirmation'" class="msg-card confirm-card">
            <template #header>{{ m.title }}</template>
            <p>{{ m.content }}</p>
            <p v-if="m.data" class="confirm-info">{{ confirmInfo(m) }}</p>
            <div v-if="m.confirm_token" class="confirm-actions">
              <el-button type="primary" :disabled="store.sending" @click="store.confirm(m.confirm_token)">
                确认执行
              </el-button>
              <el-button :disabled="store.sending" @click="cancelMsg(m)">取消</el-button>
            </div>
          </el-card>
        </template>
        <div v-if="store.sending" class="msg typing">智能体思考中…</div>
      </div>

      <div class="quick-prompts">
        <el-tag v-for="p in quickPrompts" :key="p" class="prompt-tag" @click="sendText(p)">
          {{ p }}
        </el-tag>
      </div>

      <footer class="input-bar">
        <el-input
          v-model="input"
          placeholder="输入指令，例如：明天上什么课 / 给明天学习方案 / 帮我选人工智能实战"
          @keyup.enter="sendText(input)"
          :disabled="store.sending"
        />
        <el-button type="primary" :loading="store.sending" @click="sendText(input)">发送</el-button>
      </footer>
    </main>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAgentStore } from '../stores/agent'

const store = useAgentStore()
const router = useRouter()
const input = ref('')
const listRef = ref(null)

const quickPrompts = ['明天上什么课', '给明天学习方案', '帮我选人工智能实战', '打开选课页面']

onMounted(async () => {
  await store.loadSessions()
  store.refreshStatus()
})

watch(
  () => store.messages,
  (list) => {
    const navMsg = list.find(m => m.navigation)
    if (navMsg) router.push(navMsg.navigation)
  }
)

watch(
  () => store.messages.length,
  () => {
    const navMsg = store.messages.find(m => m.navigation)
    if (navMsg) router.push(navMsg.navigation)
    scrollToBottom()
  }
)

watch(
  () => store.loadingHistory,
  (loading) => {
    if (!loading) scrollToBottom()
  }
)

function isPlan(m) {
  return !!(planOf(m) && Array.isArray(planOf(m).courses))
}

function planOf(m) {
  try {
    return JSON.parse(m.content)
  } catch {
    return null
  }
}

function priorityType(p) {
  if (p === '高') return 'danger'
  if (p === '中') return 'warning'
  return 'info'
}

function confirmInfo(m) {
  const d = m.data || {}
  const weekday = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
  const parts = []
  if (d.course) parts.push(d.course)
  if (d.day_of_week) parts.push(`${weekday[d.day_of_week - 1] || ''} ${d.period || ''}节`.trim())
  else if (d.day) parts.push(d.period ? `${d.day} ${d.period}节` : d.day)
  if (d.classroom) parts.push(d.classroom)
  if (d.week) parts.push(`第${d.week}周`)
  if (d.enrolled !== undefined && d.capacity !== undefined) parts.push(`余量 ${d.enrolled}/${d.capacity}`)
  if (d.start_date && d.end_date) parts.push(`${d.start_date} 至 ${d.end_date}（共 ${d.total_days} 天）`)
  if (d.location) parts.push(d.location)
  if (d.type) parts.push(d.type)
  if (d.description) parts.push(d.description)
  if (d.reason) parts.push(`原因：${d.reason}`)
  return parts.join('｜')
}

function sendText(text) {
  if (!text || !text.trim() || store.sending) return
  store.send(text.trim())
  input.value = ''
  scrollToBottom()
}

function sessionTitle(s) {
  const msgs = store.sessionCache[s.session_id]
  const firstUser = msgs?.find(m => m.own)?.content
  if (firstUser) return firstUser.length > 20 ? firstUser.slice(0, 20) + '…' : firstUser
  return `会话 ${s.message_count} 条`
}

function scrollToBottom() {
  nextTick(() => {
    const el = listRef.value
    if (!el) return
    // 找到最近的滚动容器；整页滚动时退回窗口滚动
    let node = el
    while (node && node !== document.body) {
      const style = getComputedStyle(node)
      if (/(auto|scroll)/.test(style.overflowY) && node.scrollHeight > node.clientHeight) {
        node.scrollTop = node.scrollHeight
        return
      }
      node = node.parentElement
    }
    window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'smooth' })
  })
}

function go(path) {
  router.push(path)
}

function cancelMsg(m) {
  const i = store.messages.indexOf(m)
  if (i >= 0) store.messages.splice(i, 1)
}
</script>

<style scoped>
.agent-layout { display: flex; min-height: calc(100vh - 48px); }
.session-panel {
  width: 220px; border-right: 1px solid #e5e7eb; background: #fff;
  display: flex; flex-direction: column; padding: 12px;
  align-self: flex-start; position: sticky; top: 0;
  height: calc(100vh - 48px);
}
.new-session-btn { width: 100%; margin-bottom: 12px; }
.session-list { flex: 1; overflow-y: auto; }
.session-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 10px; border-radius: 8px; cursor: pointer; margin-bottom: 4px;
}
.session-item:hover { background: #f3f4f6; }
.session-item.active { background: #e0e7ff; }
.session-title { font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chat-panel {
  flex: 1; display: flex; flex-direction: column; min-width: 0; min-height: 0;
}
.chat-header {
  display: flex; align-items: center; gap: 12px; padding: 12px 20px;
  border-bottom: 1px solid #e5e7eb; background: #fff;
  position: sticky; top: 0; z-index: 20;
}
.chat-header h2 { font-size: 16px; margin: 0; }
.model-status { font-size: 12px; color: #f59e0b; }
.model-status.ok { color: #10b981; }
.message-list {
  flex: 1; padding: 20px; display: flex; flex-direction: column; gap: 12px;
}
.msg {
  max-width: 75%; padding: 10px 14px; border-radius: 12px; background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08); white-space: pre-wrap;
  overflow-wrap: anywhere; word-break: break-word; align-self: flex-start;
}
.msg.own { align-self: flex-end; background: #2563eb; color: #fff; }
.msg.error { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.msg.summary { background: transparent; color: #9ca3af; font-size: 12px; align-self: center; }
.msg.typing { color: #9ca3af; font-style: italic; }
.msg-card { max-width: 80%; align-self: flex-start; }
.card-head { display: flex; align-items: center; justify-content: space-between; }
.card-content pre {
  margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; word-break: break-word;
  font-family: inherit; font-size: 13px;
}
.plan-box { display: flex; flex-direction: column; gap: 10px; }
.plan-summary { margin: 0; font-weight: 600; color: #1e293b; }
.plan-item {
  border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px 12px;
  background: #f8fafc;
}
.plan-item-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.plan-item-head strong { color: #1e293b; font-size: 14px; }
.plan-duration { margin-left: auto; color: #9ca3af; font-size: 12px; }
.plan-line { margin: 3px 0; font-size: 13px; color: #374151; line-height: 1.6; }
.plan-label {
  display: inline-block; min-width: 30px; margin-right: 6px;
  font-size: 12px; color: #2563eb; font-weight: 600;
}
.confirm-info { color: #6b7280; font-size: 13px; }
.confirm-actions { display: flex; gap: 8px; margin-top: 8px; }
.quick-prompts { padding: 8px 20px; display: flex; gap: 8px; flex-wrap: wrap; }
.prompt-tag { cursor: pointer; }
.input-bar {
  display: flex; gap: 8px; padding: 12px 20px; border-top: 1px solid #e5e7eb; background: #fff;
  position: sticky; bottom: 0; z-index: 20;
}
@media (max-width: 768px) {
  .input-bar { bottom: 56px; }
}
</style>
