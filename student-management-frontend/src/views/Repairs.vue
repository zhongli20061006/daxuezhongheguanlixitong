<template>
  <div style="padding:20px">
    <h2 style="margin-bottom:16px">报修中心</h2>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="提交报修" name="submit">
        <el-form :model="form" label-width="80px" style="max-width:500px">
          <el-form-item label="报修类型">
            <el-select v-model="form.type" style="width:100%">
              <el-option v-for="t in types" :key="t" :label="t" :value="t" />
            </el-select>
          </el-form-item>
          <el-form-item label="报修地点">
            <el-input v-model="form.location" />
          </el-form-item>
          <el-form-item label="故障描述">
            <el-input v-model="form.description" type="textarea" :rows="4" maxlength="500" show-word-limit />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="submitting" @click="submitRepair">提交报修</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
      <el-tab-pane label="我的报修" name="list">
        <el-select v-model="statusFilter" placeholder="筛选状态" clearable @change="fetchRepairs" style="margin-bottom:12px">
          <el-option v-for="s in statuses" :key="s" :label="s" :value="s" />
        </el-select>
        <div v-loading="loading">
          <el-card v-for="r in repairs" :key="r.id" class="repair-card" style="margin-bottom:12px">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <div>
                <el-tag size="small" style="margin-right:8px">{{ r.type }}</el-tag>
                <el-tag :type="statusType(r.status)" size="small">{{ r.status }}</el-tag>
              </div>
              <span style="color:#999;font-size:12px">{{ r.submit_time }}</span>
            </div>
            <p style="margin:8px 0"><b>地点：</b>{{ r.location }}</p>
            <p style="margin:4px 0;color:#666">{{ r.description }}</p>
            <div style="margin-top:8px;display:flex;gap:8px">
              <el-button v-if="r.status === '提交'" type="danger" size="small" @click="cancelRepair(r.id)">取消报修</el-button>
              <el-button v-if="r.status === '已接单'" type="danger" size="small" @click="cancelRepair(r.id)">取消报修</el-button>
              <el-button v-if="r.status === '已完成'" type="success" size="small" @click="confirmRepair(r.id)">确认完成</el-button>
            </div>
          </el-card>
          <el-empty v-if="!repairs.length && !loading" description="暂无报修记录" />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createRepair, getRepairs, updateRepairStatus } from '../api/repair'

const activeTab = ref('submit')
const types = ['水电设备', '电子产品', '家具类', '教学用具']
const statuses = ['提交', '已接单', '处理中', '已完成', '已确认', '已取消']
const form = ref({ type: '电子产品', location: '', description: '' })
const repairs = ref([])
const loading = ref(false)
const submitting = ref(false)
const statusFilter = ref('')

function statusType(v) {
  const map = { '提交':'info','已接单':'warning','处理中':'','已完成':'success','已确认':'success','已取消':'danger' }
  return map[v] || 'info'
}

async function submitRepair() {
  submitting.value = true
  try {
    await createRepair({ ...form.value })
    ElMessage.success('报修提交成功')
    form.value = { type: '电子产品', location: '', description: '' }
    activeTab.value = 'list'
    fetchRepairs()
  } catch (e) {
    const detail = e?.response?.data?.detail || '报修提交失败'
    ElMessage.error(detail)
  } finally { submitting.value = false }
}

async function fetchRepairs() {
  loading.value = true
  try {
    const res = await getRepairs(statusFilter.value || undefined)
    repairs.value = res.repairs || []
  } finally { loading.value = false }
}

async function cancelRepair(id) {
  try {
    await ElMessageBox.confirm('确定取消报修？', '确认')
    await updateRepairStatus(id, '已取消')
    ElMessage.success('已取消')
    fetchRepairs()
  } catch { /* 用户取消 */ }
}

async function confirmRepair(id) {
  try {
    await ElMessageBox.confirm('确认报修已完成？', '确认')
    await updateRepairStatus(id, '已确认')
    ElMessage.success('已确认')
    fetchRepairs()
  } catch { /* 用户取消 */ }
}

onMounted(() => fetchRepairs())
</script>
