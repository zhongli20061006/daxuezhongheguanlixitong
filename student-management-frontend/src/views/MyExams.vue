<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-header-icon" style="background:var(--color-danger-bg);color:var(--color-danger)">📋</div>
      <div>
        <h2 class="page-title" style="margin:0">我的考试</h2>
        <div class="page-subtitle">查看考试安排与考场信息</div>
      </div>
    </div>
    <el-empty v-if="!exams.length" description="暂无考试安排" :image-size="80" />
    <div v-else class="exam-timeline">
      <div v-for="e in exams" :key="e.id" class="content-card card-accent--info" style="display:flex;gap:16px;align-items:flex-start">
        <div style="min-width:80px;text-align:center">
<div style="font-size:24px;font-weight:700;color:var(--color-primary)">{{ e.date?.slice(5) }}</div>
    <div style="font-size:13px;color:var(--color-text-tertiary)">{{ e.start_time }}-{{ e.end_time }}</div>
        </div>
        <div style="flex:1">
          <div style="font-weight:600;font-size:16px;margin-bottom:4px">{{ e.subject_name }}</div>
    <div style="color:var(--color-text-tertiary);font-size:13px">🏫 {{ e.classroom_name }} | 💺 {{ e.seat_no }}号 | ⏱ {{ e.duration_minutes }}分钟</div>
          <div style="margin-top:4px"><el-tag :type="statusType(e.status)" size="small">{{ e.status }}</el-tag></div>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { getMyExams } from '../api/exam'
const exams = ref([])
function statusType(s) { const m={'已排考':'warning','已发布':'success','已结束':'info'}; return m[s]||'info' }
onMounted(async () => { try { const r = await getMyExams(); exams.value = r.exams || [] } catch {} })
</script>

<style scoped>
.exam-timeline { display:flex; flex-direction:column; gap:var(--space-md); }
</style>
