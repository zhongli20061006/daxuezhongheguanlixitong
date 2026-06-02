<template>
  <div class="page-container">
    <h2 class="page-title">请假申请</h2>
    <el-button type="primary" @click="dialogVisible=true" style="margin-bottom:16px">提交请假申请</el-button>
    <div class="content-card">
      <el-table :data="leaves" border stripe v-loading="loading" empty-text="暂无请假记录">
        <el-table-column prop="id" label="编号" width="60" />
        <el-table-column prop="start_date" label="开始日期" width="110" />
        <el-table-column prop="end_date" label="结束日期" width="110" />
        <el-table-column prop="total_days" label="天数" width="60" />
        <el-table-column prop="reason" label="原因" min-width="180" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="130"><template #default="{row}"><el-tag :type="statusType(row.status)">{{ row.status }}</el-tag></template></el-table-column>
        <el-table-column prop="submit_time" label="提交时间" width="140" />
        <el-table-column label="操作" width="100"><template #default="{row}"><el-button size="small" text type="primary" @click="showDetail(row.id)">详情</el-button><el-button v-if="['提交','审批中(辅导员)','审批中(学院)'].includes(row.status)" size="small" text type="danger" @click="handleCancel(row.id)">撤销</el-button></template></el-table-column>
      </el-table>
    </div>
    <el-dialog v-model="dialogVisible" title="提交请假申请" width="480px">
      <div class="content-card">
        <el-form :model="form" label-width="80px">
          <el-form-item label="开始日期"><el-date-picker v-model="form.start_date" type="date" placeholder="选择开始日期" /></el-form-item>
          <el-form-item label="结束日期"><el-date-picker v-model="form.end_date" type="date" placeholder="选择结束日期" /></el-form-item>
          <el-form-item label="请假原因"><el-input v-model="form.reason" type="textarea" :rows="3" maxlength="500" show-word-limit /></el-form-item>
        </el-form>
      </div>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" @click="submitApply" :loading="submitting">提交</el-button></template>
    </el-dialog>
    <el-dialog v-model="detailVisible" title="请假详情" width="520px">
      <div v-if="detail">
        <div class="content-card">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="编号">{{ detail.leave.id }}</el-descriptions-item>
            <el-descriptions-item label="状态"><el-tag :type="statusType(detail.leave.status)">{{ detail.leave.status }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="开始日期">{{ detail.leave.start_date }}</el-descriptions-item>
            <el-descriptions-item label="结束日期">{{ detail.leave.end_date }}</el-descriptions-item>
            <el-descriptions-item label="天数">{{ detail.leave.total_days }}</el-descriptions-item>
            <el-descriptions-item label="提交时间">{{ detail.leave.submit_time }}</el-descriptions-item>
            <el-descriptions-item label="原因" :span="2">{{ detail.leave.reason }}</el-descriptions-item>
          </el-descriptions>
        </div>
        <h4 style="margin:12px 0">审批记录</h4>
        <el-table v-if="detail.approvals.length" :data="detail.approvals" border size="small">
          <el-table-column prop="approver_id" label="审批人" width="120" />
          <el-table-column prop="level" label="级别" width="60"><template #default="{row}">{{ row.level===1?'辅导员':'学院' }}</template></el-table-column>
          <el-table-column prop="result" label="结果" width="70"><template #default="{row}"><el-tag :type="row.result==='通过'?'success':'danger'" size="small">{{ row.result }}</el-tag></template></el-table-column>
          <el-table-column prop="comment" label="意见" min-width="120" show-overflow-tooltip />
          <el-table-column prop="created_at" label="时间" width="140" />
        </el-table>
        <el-empty v-else description="暂无审批记录" />
      </div>
    </el-dialog>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { getMyLeaves, applyLeave, cancelLeave, getLeaveDetail } from '../api/leave'
import { ElMessage, ElMessageBox } from 'element-plus'
const leaves=ref([]); const loading=ref(false); const dialogVisible=ref(false); const detailVisible=ref(false); const submitting=ref(false); const detail=ref(null)
const form=ref({ start_date:null, end_date:null, reason:'' })
function statusType(s){ const m={'提交':'info','审批中(辅导员)':'warning','审批中(学院)':'warning','已通过':'success','已驳回':'danger','已撤销':'info'}; return m[s]||'info' }
async function load(){ loading.value=true; try{const r=await getMyLeaves(); leaves.value=r.leaves||[]}catch{ElMessage.error('加载失败')}finally{loading.value=false} }
async function submitApply(){ if(!form.value.start_date||!form.value.end_date||!form.value.reason){ElMessage.warning('请填写完整');return} submitting.value=true; try{const fmt=d=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;const data={start_date:fmt(form.value.start_date),end_date:fmt(form.value.end_date),reason:form.value.reason};await applyLeave(data);ElMessage.success('已提交');dialogVisible.value=false;form.value={start_date:null,end_date:null,reason:''};load()}catch(e){ElMessage.error(e?.response?.data?.detail||'提交失败')}finally{submitting.value=false} }
async function handleCancel(id){ try{await ElMessageBox.confirm('确定撤销？','确认');await cancelLeave(id);ElMessage.success('已撤销');load()}catch{} }
async function showDetail(id){ try{const r=await getLeaveDetail(id);detail.value=r;detailVisible.value=true}catch{ElMessage.error('加载详情失败')} }
onMounted(load)
</script>
