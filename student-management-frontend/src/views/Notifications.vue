<template>
  <div class="page">
    <h2>通知中心</h2>
    <div style="margin-bottom: 16px">
      <el-button type="primary" size="small" @click="handleReadAll" :disabled="!hasUnread">全部已读</el-button>
    </div>
    <el-empty v-if="items.length === 0" description="暂无通知" />
    <div v-else class="notif-list">
      <div
        v-for="item in items"
        :key="item.id"
        class="notif-item"
        :class="{ unread: !item.is_read }"
        @click="handleRead(item)"
      >
        <div class="notif-header">
          <el-tag size="small" :type="item.is_read ? 'info' : 'danger'">{{ item.is_read ? '已读' : '未读' }}</el-tag>
          <span class="notif-title">{{ item.title }}</span>
          <span class="notif-time">{{ item.created_at }}</span>
        </div>
        <div class="notif-content">{{ item.content }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { getNotifications, markAsRead, markAllRead } from '../api/notification'
import { ElMessage } from 'element-plus'

const items = ref([])

const hasUnread = computed(() => items.value.some(item => !item.is_read))

async function load() {
  try {
    const res = await getNotifications()
    items.value = res.notifications
  } catch { ElMessage.error('加载通知失败') }
}

async function handleRead(item) {
  if (!item.is_read) {
    try {
      await markAsRead(item.id)
      item.is_read = true
    } catch {}
  }
}

async function handleReadAll() {
  try {
    await markAllRead()
    items.value.forEach(item => { item.is_read = true })
    ElMessage.success('已全部标记为已读')
  } catch { ElMessage.error('操作失败') }
}

onMounted(load)
</script>

<style scoped>
.page { max-width: 800px; margin: 20px auto; padding: 0 16px; }
.notif-list { display: flex; flex-direction: column; gap: 12px; }
.notif-item { padding: 14px 16px; border: 1px solid #e6e6e6; border-radius: 8px; cursor: pointer; transition: background 0.2s; }
.notif-item:hover { background: #f5f7fa; }
.notif-item.unread { border-left: 3px solid #f56c6c; background: #fef0f0; }
.notif-header { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.notif-title { font-weight: 600; font-size: 15px; }
.notif-time { color: #999; font-size: 13px; margin-left: auto; }
.notif-content { color: #666; font-size: 14px; line-height: 1.6; }
</style>
