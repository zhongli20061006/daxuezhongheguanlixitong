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

/* ── Exam Card Grid ── */
div[style*="grid-template-columns:repeat(3,1fr)"] {
  gap: var(--space-md) !important;
  animation: fadeInUp 0.4s ease-out;
}

/* ── Exam Card Content (content-card children) ── */
.content-card {
  border-left: 4px solid var(--color-info);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition-base), box-shadow var(--transition-base);
  cursor: default;
  padding: var(--space-lg);
  border: 1px solid var(--color-border-light);
}
.content-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

/* ── Subject Name ── */
div[style*="font-weight:600;font-size:15px"] {
  color: var(--color-text-primary) !important;
  margin-bottom: 8px;
  font-size: 16px !important;
}

/* ── Status Tag Spacing ── */
.el-tag[size="small"] {
  margin-top: 6px;
}

/* ── Empty State Enhancement ── */
.el-empty__description {
  color: var(--color-text-muted);
  font-size: 14px;
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .page-title { font-size: 19px; }
  div[style*="grid-template-columns:repeat(3,1fr)"] {
    grid-template-columns: 1fr !important;
  }
}
</style>
