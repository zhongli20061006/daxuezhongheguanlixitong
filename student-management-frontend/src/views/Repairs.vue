<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-header-icon" style="background:var(--color-warning-bg);color:var(--color-warning)">🔧</div>
      <div>
        <h2 class="page-title" style="margin:0">报修中心</h2>
        <div class="page-subtitle">提交报修申请与跟踪维修进度</div>
      </div>
    </div>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="提交报修" name="submit">
        <div class="content-card card-accent--warning" style="max-width:500px">
          <el-form :model="form" label-width="80px">
            <el-form-item label="报修类型"><el-select v-model="form.type" style="width:100%"><el-option v-for="t in types" :key="t" :label="typeIcons[t]+' '+t" :value="t" /></el-select></el-form-item>
            <el-form-item label="报修地点"><el-input v-model="form.location" /></el-form-item>
            <el-form-item label="故障描述"><el-input v-model="form.description" type="textarea" :rows="3" maxlength="500" show-word-limit /></el-form-item>
            <el-form-item><el-button type="primary" :loading="submitting" @click="submitRepair">提交报修</el-button></el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
      <el-tab-pane label="我的报修" name="list">
        <el-select v-model="statusFilter" placeholder="筛选状态" clearable @change="fetchRepairs" style="margin-bottom:12px"><el-option v-for="s in statuses" :key="s" :label="s" :value="s" /></el-select>
        <div v-loading="loading">
          <div v-for="r in repairs" :key="r.id" class="content-card card-left-accent">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
              <div style="display:flex;gap:8px;"><el-tag size="small">{{ r.type }}</el-tag><el-tag :type="statusType(r.status)" size="small">{{ r.status }}</el-tag></div>
    <span style="color:var(--color-text-muted);font-size:12px">{{ r.submit_time }}</span>
            </div>
            <p style="margin:4px 0"><b>地点：</b>{{ r.location }}</p>
    <p style="color:var(--color-text-tertiary);font-size:14px">{{ r.description }}</p>
            <div style="margin-top:8px;display:flex;gap:8px">
              <el-button v-if="r.status==='提交'" type="danger" size="small" @click="cancelRepair(r.id)">取消</el-button>
              <el-button v-if="r.status==='已接单'" type="danger" size="small" @click="cancelRepair(r.id)">取消</el-button>
              <el-button v-if="r.status==='已完成'" type="success" size="small" @click="confirmRepair(r.id)">确认完成</el-button>
            </div>
          </div>
          <el-empty v-if="!repairs.length&&!loading" description="暂无报修" :image-size="80" />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createRepair, getRepairs, updateRepairStatus } from '../api/repair'
const activeTab=ref('submit'); const types=['水电设备','电子产品','家具类','教学用具']; const statuses=['提交','已接单','处理中','已完成','已确认','已取消']
const typeIcons={'水电设备':'⚡','电子产品':'💻','家具类':'🪑','教学用具':'📚'}
const form=ref({ type:'电子产品', location:'', description:'' }); const repairs=ref([]); const loading=ref(false); const submitting=ref(false); const statusFilter=ref('')
function statusType(v){const m={'提交':'info','已接单':'warning','处理中':'','已完成':'success','已确认':'success','已取消':'danger'};return m[v]||'info'}
async function submitRepair(){submitting.value=true;try{await createRepair({...form.value});ElMessage.success('提交成功');form.value={ type:'电子产品',location:'',description:'' };activeTab.value='list';fetchRepairs()}catch(e){ElMessage.error(e?.response?.data?.detail||'提交失败')}finally{submitting.value=false}}
async function fetchRepairs(){loading.value=true;try{const r=await getRepairs(statusFilter.value||undefined);repairs.value=r.repairs||[]}finally{loading.value=false}}
async function cancelRepair(id){try{await ElMessageBox.confirm('确定取消？','确认');await updateRepairStatus(id,'已取消');ElMessage.success('已取消');fetchRepairs()}catch{}}
async function confirmRepair(id){try{await ElMessageBox.confirm('确认完成？','确认');await updateRepairStatus(id,'已确认');ElMessage.success('已确认');fetchRepairs()}catch{}}
onMounted(()=>fetchRepairs())
</script>
