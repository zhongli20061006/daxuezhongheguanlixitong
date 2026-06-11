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
          <span style="color:#6B7280;font-size:13px">共 {{ filteredItems.length }} 条</span>
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
            <span style="color:#9CA3AF;font-size:12px;white-space:nowrap">{{ item.created_at }}</span>
            <el-button text type="danger" size="small" @click.stop="handleDelete(item)">删除</el-button>
          </div>
          <div style="color:#6B7280;font-size:13px;margin-top:4px;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical" @click="handleRead(item)">{{ item.content }}</div>
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
    await ElMessageBox.confirm('将清除所有 7 天前的已读通知，确定？', '清理确认', { type: 'warning' })
    const r = await cleanupRead(7)
    await load()
    ElMessage.success(r.message || '清理完成')
  } catch {}
}
onMounted(load)
</script>
<style scoped>
.notif-nav-item { display:flex; justify-content:space-between; align-items:center; padding:10px 12px; cursor:pointer; border-radius:6px; margin-bottom:4px; font-size:14px; }
.notif-nav-item:hover { background:#F3F4F6; }
.notif-nav-item.active { background:#EFF6FF; color:#2563EB; font-weight:600; }
.notif-item { padding:14px 16px; border:1px solid #E5E7EB; border-radius:8px; margin-bottom:8px; cursor:pointer; }
.notif-item:hover { background:#F9FAFB; }
.notif-item.unread { border-left:3px solid #2563EB; background:#F0F5FF; }
.notif-flex { display:flex; align-items:center; gap:8px; }
.unread-dot { width:8px; height:8px; border-radius:50%; background:#2563EB; flex-shrink:0; }
@media (max-width:768px) { div[style*="display:flex;gap:24px"] { flex-direction:column; } div[style*="width:180px"] { width:100%!important; display:flex; gap:6px; overflow-x:auto; } }
</style>
