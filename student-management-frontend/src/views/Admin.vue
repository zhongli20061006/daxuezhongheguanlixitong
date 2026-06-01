<template>
  <div style="padding:20px">
    <h2 style="margin-bottom:16px">管理后台</h2>
    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <!-- 课表管理 -->
      <el-tab-pane label="课表管理" name="schedule">
        <div style="display:flex;gap:12px;margin-bottom:12px;align-items:center">
          <el-select v-model="adminClassId" placeholder="选择班级" style="width:200px" @change="loadSchedules">
            <el-option v-for="c in classOptions" :key="c" :label="`班级${c}`" :value="c" />
          </el-select>
          <el-button type="primary" @click="showScheduleDialog(null)">新增排课</el-button>
        </div>
        <el-table :data="schedules" v-loading="schLoading" stripe>
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="course_name" label="课程" />
          <el-table-column prop="teacher_name" label="教师" />
          <el-table-column prop="classroom_name" label="教室" />
          <el-table-column label="时间">
            <template #default="{row}"> 周{{ row.day_of_week }} {{ row.period }}节 </template>
          </el-table-column>
          <el-table-column prop="weeks" label="周次" />
          <el-table-column label="操作" width="150">
            <template #default="{row}">
              <el-button size="small" @click="showScheduleDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteSch(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <!-- 选课设置 -->
      <el-tab-pane label="选课设置" name="window">
        <el-form :model="windowForm" label-width="120px" style="max-width:500px">
          <el-form-item label="选课开始时间">
            <el-input v-model="windowForm.selection_start_time" placeholder="YYYY-MM-DD HH:MM:SS" />
          </el-form-item>
          <el-form-item label="选课结束时间">
            <el-input v-model="windowForm.selection_end_time" placeholder="YYYY-MM-DD HH:MM:SS" />
          </el-form-item>
          <el-form-item label="退课截止时间">
            <el-input v-model="windowForm.drop_deadline" placeholder="YYYY-MM-DD HH:MM:SS" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveWindow">保存</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
      <!-- 用户管理 -->
      <el-tab-pane label="用户管理" name="users">
        <el-table :data="users" v-loading="userLoading" stripe>
          <el-table-column prop="username" label="用户名" />
          <el-table-column label="角色">
            <template #default="{row}"><el-tag size="small">{{ row.role }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="role_id" label="角色ID" />
          <el-table-column label="操作" width="120">
            <template #default="{row}">
              <el-button size="small" type="warning" @click="resetPwd(row)">重置密码</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
    <!-- 排课弹窗 -->
    <el-dialog :title="schEdit.id ? '编辑排课' : '新增排课'" v-model="schDialogVisible" width="500px">
      <el-form :model="schEdit" label-width="80px">
        <el-form-item label="教师ID"><el-input-number v-model="schEdit.teacher_id" /></el-form-item>
        <el-form-item label="科目ID"><el-input-number v-model="schEdit.subject_id" /></el-form-item>
        <el-form-item label="班级ID"><el-input-number v-model="schEdit.class_id" /></el-form-item>
        <el-form-item label="教室ID"><el-input-number v-model="schEdit.classroom_id" /></el-form-item>
        <el-form-item label="星期"><el-input-number v-model="schEdit.day_of_week" :min="1" :max="7" /></el-form-item>
        <el-form-item label="节次"><el-input v-model="schEdit.period" placeholder="1-2" /></el-form-item>
        <el-form-item label="周次"><el-input v-model="schEdit.weeks" placeholder="1-18" /></el-form-item>
        <el-form-item label="学期"><el-input v-model="schEdit.semester" placeholder="2024-2025-1" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="schDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveSchedule">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as scheduleApi from '../api/schedule'
import { setSelectionWindow, getSelectionWindow, getUsers, resetPassword } from '../api/admin'

const activeTab = ref('schedule')
const adminClassId = ref(1)
const classOptions = [1, 2, 3]
const schedules = ref([])
const schLoading = ref(false)
const schDialogVisible = ref(false)
const schEdit = ref({})
const windowForm = ref({ selection_start_time: '', selection_end_time: '', drop_deadline: '' })
const users = ref([])
const userLoading = ref(false)

async function loadSchedules() {
  schLoading.value = true
  try {
    const res = await scheduleApi.getClassSchedule(adminClassId.value)
    schedules.value = res.schedules || []
  } finally { schLoading.value = false }
}

function showScheduleDialog(row) {
  schEdit.value = row ? { ...row } : { teacher_id: null, subject_id: null, class_id: 1, classroom_id: null, day_of_week: 1, period: '1-2', weeks: '1-18', semester: '2024-2025-1' }
  schDialogVisible.value = true
}

async function saveSchedule() {
  try {
    if (schEdit.value.id) {
      await scheduleApi.updateSchedule(schEdit.value.id, schEdit.value)
    } else {
      await scheduleApi.createSchedule(schEdit.value)
    }
    ElMessage.success('保存成功')
    schDialogVisible.value = false
    loadSchedules()
  } catch (e) {
    const detail = e?.response?.data?.detail || '保存失败，请检查所有字段是否填写正确'
    ElMessage.error(detail)
  }
}

async function deleteSch(row) {
  try {
    await ElMessageBox.confirm('确定删除？', '确认')
    await scheduleApi.deleteSchedule(row.id)
    ElMessage.success('已删除')
    loadSchedules()
  } catch { /* 用户取消 */ }
}

async function saveWindow() {
  await setSelectionWindow(windowForm.value)
  ElMessage.success('保存成功')
}

async function loadUsers() {
  userLoading.value = true
  try {
    const res = await getUsers()
    users.value = res.users || []
  } finally { userLoading.value = false }
}

async function resetPwd(row) {
  try {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
    const array = new Uint8Array(8)
    crypto.getRandomValues(array)
    const newPwd = Array.from(array).map(b => chars[b % chars.length]).join('')
    await ElMessageBox.confirm(`确定重置 ${row.username} 的密码为 ${newPwd}？`, '确认')
    await resetPassword(row.id, newPwd)
    ElMessage.success(`密码已重置为: ${newPwd}`)
  } catch {}
}

function onTabChange(tab) {
  if (tab === 'users') loadUsers()
}

onMounted(async () => {
  await loadSchedules()
  try {
    const res = await getSelectionWindow()
    windowForm.value = { ...windowForm.value, ...res }
  } catch {}
})
</script>
