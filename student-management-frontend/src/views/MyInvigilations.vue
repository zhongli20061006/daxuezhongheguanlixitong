<template>
  <div class="page-container">
    <h2 class="page-title">监考安排</h2>
    <el-empty v-if="!exams.length" description="暂无监考安排" :image-size="80" />
    <div v-else style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
      <div v-for="e in exams" :key="e.id" class="content-card">
        <div style="font-weight:600;font-size:15px">{{ e.subject_name }}</div>
        <div style="color:#6B7280;font-size:13px;margin:4px 0">{{ e.date }} {{ e.start_time }}-{{ e.end_time }}</div>
        <div style="color:#6B7280;font-size:13px">🏫 {{ e.classroom_name }}</div>
        <el-tag :type="statusType(e.status)" size="small" style="margin-top:4px">{{ e.status }}</el-tag>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { getMyInvigilations } from '../api/exam'
const exams = ref([])
function statusType(s) { const m={'已排考':'warning','已发布':'success','已结束':'info'}; return m[s]||'info' }
onMounted(async () => { try { const r = await getMyInvigilations(); exams.value = r.exams || [] } catch {} })
</script>
<style scoped>@media (max-width:768px){div[style*="grid-template-columns:repeat(3,1fr)"]{grid-template-columns:1fr!important}}</style>
