<template>
  <div class="page-container">
    <h2 class="page-title">报修管理</h2>
    <div class="content-card">
      <div style="display:flex;gap:12px;margin-bottom:12px"><el-select v-model="statusFilter" placeholder="状态筛选" clearable @change="fetchRepairs"><el-option v-for="s in statuses" :key="s" :label="s" :value="s" /></el-select><el-select v-model="typeFilter" placeholder="类型筛选" clearable @change="fetchRepairs"><el-option v-for="t in types" :key="t" :label="t" :value="t" /></el-select></div>
      <el-table :data="repairs" v-loading="loading" stripe>
        <el-table-column prop="id" label="编号" width="60" />
        <el-table-column prop="user_id" label="报修人" width="100" />
        <el-table-column label="类型" width="100"><template #default="{row}"><el-tag size="small">{{ row.type }}</el-tag></template></el-table-column>
        <el-table-column prop="location" label="地点" width="120" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column label="状态" width="100"><template #default="{row}"><el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag></template></el-table-column>
        <el-table-column prop="submit_time" label="提交时间" width="160" />
        <el-table-column label="操作" width="160" fixed="right"><template #default="{row}"><el-button v-if="row.status==='提交'" type="primary" size="small" @click="updateStatus(row.id,'已接单')">接单</el-button><el-button v-if="row.status==='已接单'" type="warning" size="small" @click="updateStatus(row.id,'处理中')">处理</el-button><el-button v-if="row.status==='处理中'" type="success" size="small" @click="updateStatus(row.id,'已完成')">完成</el-button></template></el-table-column>
      </el-table>
      <el-empty v-if="!repairs.length&&!loading" description="暂无报修" :image-size="80" />
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getRepairs, updateRepairStatus } from '../api/repair'
const statuses=['提交','已接单','处理中','已完成','已确认','已取消']; const types=['水电设备','电子产品','家具类','教学用具']
const repairs=ref([]); const loading=ref(false); const statusFilter=ref(''); const typeFilter=ref('')
function statusType(v){const m={'提交':'info','已接单':'warning','处理中':'','已完成':'success','已确认':'success','已取消':'danger'};return m[v]||'info'}
async function fetchRepairs(){loading.value=true;try{const r=await getRepairs(statusFilter.value||undefined);repairs.value=r.repairs||[]}finally{loading.value=false}}
async function updateStatus(id,s){try{await updateRepairStatus(id,s);ElMessage.success('状态更新成功');fetchRepairs()}catch{}}
onMounted(fetchRepairs)
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
  background: var(--color-warning);
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

/* ── Content Card Accent (repair page) ── */
.content-card {
  border-top: 3px solid var(--color-warning);
  animation: fadeInUp 0.35s ease-out;
}

/* ── Filter Area Enhancement ── */
div[style*="display:flex;gap:12px;margin-bottom:12px"] {
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border-light);
  margin-bottom: 16px !important;
  gap: 12px;
}

/* ── Empty State Enhancement ── */
.el-empty__description {
  color: var(--color-text-muted);
  font-size: 14px;
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .page-title { font-size: 19px; }
  div[style*="display:flex;gap:12px;margin-bottom:12px"] {
    flex-wrap: wrap;
  }
}
</style>
