<template>
  <div class="page">
    <h2>请假审批</h2>
    <el-table :data="leaves" border stripe v-loading="loading" empty-text="暂无待审批请假">
      <el-table-column prop="id" label="编号" width="60" />
      <el-table-column prop="student_name" label="学生姓名" width="100" />
      <el-table-column prop="student_id" label="学号" width="110" />
      <el-table-column prop="start_date" label="开始日期" width="110" />
      <el-table-column prop="end_date" label="结束日期" width="110" />
      <el-table-column prop="total_days" label="天数" width="60" />
      <el-table-column prop="reason" label="原因" min-width="160" show-overflow-tooltip />
      <el-table-column prop="status" label="状态" width="130">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="submit_time" label="提交时间" width="140" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="success" @click="handleApprove(row, '通过')">通过</el-button>
          <el-button size="small" type="danger" @click="handleApprove(row, '驳回')">驳回</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="commentVisible" title="审批意见" width="400px">
      <el-input v-model="comment" type="textarea" :rows="3" placeholder="选填" maxlength="200" show-word-limit />
      <template #footer>
        <el-button @click="commentVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmApprove">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getPendingApprovals, approveLeave } from '../api/leave'
import { ElMessage } from 'element-plus'

const leaves = ref([])
const loading = ref(false)
const commentVisible = ref(false)
const comment = ref('')
let pendingAction = null

function statusType(status) {
  const map = { '审批中(辅导员)': 'warning', '审批中(学院)': 'warning' }
  return map[status] || 'info'
}

async function load() {
  loading.value = true
  try {
    const res = await getPendingApprovals()
    leaves.value = res.leaves
  } catch { ElMessage.error('加载失败') }
  finally { loading.value = false }
}

function handleApprove(row, result) {
  pendingAction = { leave_id: row.id, result }
  comment.value = ''
  commentVisible.value = true
}

async function confirmApprove() {
  try {
    await approveLeave({ leave_id: pendingAction.leave_id, result: pendingAction.result, comment: comment.value || null })
    ElMessage.success(pendingAction.result === '通过' ? '已通过' : '已驳回')
    commentVisible.value = false
    load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

onMounted(load)
</script>

<style scoped>
/* ── Page Layout Enhancement ── */
.page {
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--space-lg);
  animation: fadeIn 0.3s ease-out;
}

/* ── Page Header Enhancement ── */
h2 {
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
h2::before {
  content: '';
  width: 4px;
  height: 24px;
  background: var(--color-warning);
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

/* ── Table Card Wrapper ── */
.el-table {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-light);
}

/* ── Empty State Enhancement ── */
.el-empty__description {
  color: var(--color-text-muted);
  font-size: 14px;
}

/* ── Dialog Enhancements ── */
.el-dialog {
  border-radius: var(--radius-lg);
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .page { padding: 12px; }
  h2 { font-size: 19px; }
}
</style>
