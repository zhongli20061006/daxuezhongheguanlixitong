<template>
  <div class="page-container">
    <h2 class="page-title">通知中心</h2>
    <div style="display:flex;gap:24px">
      <div style="width:180px;flex-shrink:0">
        <div v-for="cat in categories" :key="cat.key" :class="['notif-nav-item',{active:cat.key===activeCategory}]" @click="activeCategory=cat.key">
          <span>{{ cat.label }}</span><el-tag v-if="cat.unread>0" type="danger" size="small">{{ cat.unread }}</el-tag>
        </div>
      </div>
      <div style="flex:1">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <span style="color:var(--color-text-tertiary);font-size:13px">共 {{ filteredItems.length }} 条</span>
          <div style="display:flex;gap:8px">
            <el-button type="primary" size="small" @click="handleReadAll" :disabled="!hasUnread">全部已读</el-button>
            <el-button type="danger" size="small" plain @click="handleCleanup" :disabled="!items.length">清除已读</el-button>
          </div>
        </div>
        <div v-for="item in filteredItems" :key="item.id" :class="['notif-item',{unread:!item.is_read}]">
          <div class="notif-flex">
            <div style="display:flex;align-items:center;gap:8px;flex:1;min-width:0" @click="handleRead(item)">
              <div v-if="!item.is_read" class="unread-dot"></div>
              <span :style="{fontWeight:item.is_read?400:700}">{{ item.title }}</span>
            </div>
    <span style="color:var(--color-text-muted);font-size:12px;white-space:nowrap">{{ item.created_at }}</span>
            <el-button text type="danger" size="small" @click.stop="handleDelete(item)">删除</el-button>
          </div>
    <div style="color:var(--color-text-tertiary);font-size:13px;margin-top:4px;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical" @click="handleRead(item)">{{ item.content }}</div>
        </div>
        <el-empty v-if="!filteredItems.length" description="暂无通知" :image-size="80" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getNotifications, markAsRead, markAllRead, deleteNotification, cleanupRead } from '../api/notification'
import { ElMessage, ElMessageBox } from 'element-plus'

const items = ref([]); const activeCategory = ref('all')
const categories = computed(() => {
  const counts = {}
  for (const item of items.value) {
    const key = item.event_type || 'system'
    if (!counts[key]) counts[key] = 0
    if (!item.is_read) counts[key]++
  }
  return [
    { key: 'all', label: '全部', unread: Object.values(counts).reduce((a,b)=>a+b,0) },
    ...Object.entries(counts).map(([k,v]) => ({ key: k, label: categoryLabel(k), unread: v })),
  ]
})
function categoryLabel(key) {
  const map = { leave_submitted:'请假通知', leave_approved:'请假通知', leave_rejected:'请假通知', score_published:'成绩通知', repair_status_changed:'报修通知', system:'系统通知' }
  return map[key] || key
}
const filteredItems = computed(() => activeCategory.value === 'all' ? items.value : items.value.filter(i => (i.event_type||'system') === activeCategory.value))
const hasUnread = computed(() => items.value.some(i => !i.is_read))

async function load() {
  try { const r = await getNotifications(200, 0); items.value = r.notifications || [] } catch {}
}
async function handleRead(item) {
  if (!item.is_read) { try { await markAsRead(item.id); item.is_read = true } catch {} }
}
async function handleReadAll() {
  try { await markAllRead(); items.value.forEach(i => i.is_read = true); ElMessage.success('已全部已读') } catch {}
}
async function handleDelete(item) {
  try {
    await ElMessageBox.confirm('确定删除该通知？', '确认', { type: 'warning' })
    await deleteNotification(item.id)
    items.value = items.value.filter(i => i.id !== item.id)
    ElMessage.success('已删除')
  } catch {}
}
async function handleCleanup() {
  try {
    await ElMessageBox.confirm('将清除所有已读通知，确定？', '清理确认', { type: 'warning' })
    const r = await cleanupRead(0)
    await load()
    ElMessage.success(r.message || '清理完成')
  } catch {}
}
onMounted(load)
</script>
<style scoped>
/* ── Page Header Enhancement ── */
.page-title {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: var(--space-lg);
  padding-bottom: var(--space-md);
  border-bottom: 2px solid var(--color-border-light);
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.3px;
}
.page-title::before {
  content: '';
  width: 4px;
  height: 24px;
  background: var(--color-info);
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

/* ── Notification Nav Sidebar ── */
.notif-nav-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  cursor: pointer;
  border-radius: var(--radius-md);
  margin-bottom: 4px;
  font-size: 14px;
  transition: all var(--transition-fast);
  color: var(--color-text-secondary);
}
.notif-nav-item:hover {
  background: var(--color-bg-alt);
  color: var(--color-text-primary);
}
.notif-nav-item.active {
  background: var(--color-primary-bg);
  color: var(--color-primary);
  font-weight: 600;
}

/* ── Notification Item Card ── */
.notif-item {
  padding: 16px 18px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  margin-bottom: 10px;
  cursor: pointer;
  transition: all var(--transition-base);
  background: var(--color-surface);
}
.notif-item:hover {
  background: var(--color-bg-alt);
  box-shadow: var(--shadow-sm);
}
.notif-item.unread {
  border-left: 3px solid var(--color-primary);
  background: var(--color-primary-bg);
}

/* ── Notification Flex Row ── */
.notif-flex {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ── Unread Dot ── */
.unread-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
  flex-shrink: 0;
  box-shadow: 0 0 4px rgba(14, 165, 233, 0.4);
}

/* ── Empty State Enhancement ── */
.el-empty__description {
  color: var(--color-text-muted);
  font-size: 14px;
}

/* ── Toolbar Area ── */
div[style*="justify-content:space-between;align-items:center;margin-bottom:12px"] {
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border-light);
  margin-bottom: 16px !important;
}

/* ── Entrance Animation ── */
.notif-item {
  animation: fadeInUp 0.3s ease-out;
}
.notif-item:nth-child(2) { animation-delay: 0.04s; }
.notif-item:nth-child(3) { animation-delay: 0.08s; }
.notif-item:nth-child(4) { animation-delay: 0.12s; }
.notif-item:nth-child(5) { animation-delay: 0.16s; }

/* ── Responsive ── */
@media (max-width: 768px) {
  .page-title { font-size: 19px; }
  div[style*="display:flex;gap:24px"] { flex-direction: column; }
  div[style*="width:180px"] { width: 100% !important; display: flex; gap: 6px; overflow-x: auto; }
  .notif-item { padding: 12px 14px; }
}
</style>
