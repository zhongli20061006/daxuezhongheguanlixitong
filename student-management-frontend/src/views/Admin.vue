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
      <!-- 培养方案 -->
      <el-tab-pane label="培养方案" name="plans">
        <div style="display:flex;gap:12px;margin-bottom:12px">
          <el-button type="primary" @click="showPlanDialog">新增方案</el-button>
        </div>
        <el-table :data="plans" v-loading="planLoading" stripe @expand-change="onPlanExpand">
          <el-table-column type="expand">
            <template #default="{ row }">
              <div style="padding:8px 20px">
                <div style="display:flex;gap:8px;margin-bottom:8px;align-items:center">
                  <span style="font-weight:bold">课程列表</span>
                  <el-button size="small" type="primary" @click="showAddCourseDialog(row)">添加课程</el-button>
                </div>
                <el-table :data="row._courses || []" size="small" border>
                  <el-table-column prop="subject_name" label="课程名" />
                  <el-table-column prop="credit" label="学分" width="70" />
                  <el-table-column label="类型" width="80">
                    <template #default="{ r }"><el-tag :type="r.course_type==='limited'?'warning':r.course_type==='elective'?'success':''" size="small">{{ typeMap2[r.course_type] }}</el-tag></template>
                  </el-table-column>
                  <el-table-column prop="limited_group" label="分组" width="120" />
                  <el-table-column prop="min_required" label="至少选" width="70" />
                  <el-table-column label="操作" width="80">
                    <template #default="{ r }">
                      <el-button size="small" type="danger" @click="deleteCourse(r.id)">删除</el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="major" label="专业" />
          <el-table-column prop="grade" label="年级" width="80" />
          <el-table-column prop="total_credits_required" label="总学分" width="80" />
          <el-table-column prop="elective_credits_required" label="选修学分" width="80" />
        </el-table>
      </el-tab-pane>
      <!-- 毕业审核 -->
      <el-tab-pane label="毕业审核" name="audit">
        <div style="display:flex;gap:12px;margin-bottom:12px;align-items:center">
          <el-input v-model="auditMajor" placeholder="专业筛选" style="width:180px" clearable />
          <el-input-number v-model="auditGrade" placeholder="年级" :min="2000" style="width:120px" />
          <el-button type="primary" @click="loadAudits">查询</el-button>
          <el-button type="success" @click="runBatchAudit">批量审核</el-button>
        </div>
        <el-table :data="audits" v-loading="auditLoading" stripe>
          <el-table-column prop="student_id" label="学号" width="110" />
          <el-table-column prop="student_name" label="姓名" width="90" />
          <el-table-column prop="major" label="专业" />
          <el-table-column label="总学分" width="120">
            <template #default="{ row }">{{ row.total_credits_earned }}/{{ row.total_credits_required }}</template>
          </el-table-column>
          <el-table-column label="必修" width="80">
            <template #default="{ row }">{{ row.compulsory_passed }}/{{ row.compulsory_total }}</template>
          </el-table-column>
          <el-table-column label="毕业" width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_graduatable ? 'success' : 'danger'" size="small">{{ row.is_graduatable ? '可毕业' : '未达标' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="详情" min-width="150" show-overflow-tooltip>
            <template #default="{ row }">{{ row.detail || '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button size="small" @click="reauditStudent(row.student_id)">重审</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
    <!-- 培养方案弹窗 -->
    <el-dialog v-model="planDialogVisible" title="新增培养方案" width="400px">
      <el-form :model="planForm" label-width="100px">
        <el-form-item label="专业"><el-input v-model="planForm.major" /></el-form-item>
        <el-form-item label="年级"><el-input-number v-model="planForm.grade" :min="2000" /></el-form-item>
        <el-form-item label="总学分"><el-input-number v-model="planForm.total_credits_required" :min="1" :precision="1" /></el-form-item>
        <el-form-item label="选修学分"><el-input-number v-model="planForm.elective_credits_required" :min="0" :precision="1" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="planDialogVisible=false">取消</el-button>
        <el-button type="primary" @click="createPlan">保存</el-button>
      </template>
    </el-dialog>
    <!-- 添加课程弹窗 -->
    <el-dialog v-model="courseDialogVisible" title="添加方案课程" width="400px">
      <el-form :model="courseForm" label-width="100px">
        <el-form-item label="科目ID"><el-input-number v-model="courseForm.subject_id" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="courseForm.course_type">
            <el-option label="必修" value="compulsory" />
            <el-option label="限选" value="limited" />
            <el-option label="选修" value="elective" />
          </el-select>
        </el-form-item>
        <el-form-item label="学分"><el-input-number v-model="courseForm.credit" :min="0" :precision="1" /></el-form-item>
        <el-form-item label="限选组"><el-input v-model="courseForm.limited_group" /></el-form-item>
        <el-form-item label="至少选"><el-input-number v-model="courseForm.min_required" :min="1" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="courseDialogVisible=false">取消</el-button>
        <el-button type="primary" @click="addCourse">确定</el-button>
      </template>
    </el-dialog>
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
import * as trainingApi from '../api/training'

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
const typeMap2 = { compulsory: '必修', limited: '限选', elective: '选修' }

// 培养方案
const plans = ref([])
const planLoading = ref(false)
const planDialogVisible = ref(false)
const planForm = ref({ major: '', grade: 2024, total_credits_required: 150, elective_credits_required: 20 })
const courseDialogVisible = ref(false)
const courseForm = ref({ subject_id: null, course_type: 'compulsory', credit: 3, limited_group: '', min_required: 2 })
let selectedPlanId = null

// 毕业审核
const audits = ref([])
const auditLoading = ref(false)
const auditMajor = ref('')
const auditGrade = ref(null)

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
  if (tab === 'plans') loadPlans()
  if (tab === 'audit') loadAudits()
}

// ====== 培养方案 ======
async function loadPlans() {
  planLoading.value = true
  try {
    const res = await trainingApi.getPlans()
    plans.value = (res.plans || []).map(p => ({ ...p, _courses: [] }))
  } finally { planLoading.value = false }
}
async function onPlanExpand(row) {
  if (row._courses.length) return
  try {
    const res = await trainingApi.getPlanCourses(row.id)
    row._courses = res.courses || []
  } catch {}
}
function showPlanDialog() { planForm.value = { major: '', grade: 2024, total_credits_required: 150, elective_credits_required: 20 }; planDialogVisible.value = true }
async function createPlan() {
  try {
    await trainingApi.createPlan(planForm.value)
    ElMessage.success('方案已创建')
    planDialogVisible.value = false
    loadPlans()
  } catch (e) { ElMessage.error(e?.response?.data?.detail || '创建失败') }
}
function showAddCourseDialog(row) { selectedPlanId = row.id; courseForm.value = { subject_id: null, course_type: 'compulsory', credit: 3, limited_group: '', min_required: null }; courseDialogVisible.value = true }
async function addCourse() {
  try {
    await trainingApi.addPlanCourse({ ...courseForm.value, plan_id: selectedPlanId })
    ElMessage.success('课程已添加')
    courseDialogVisible.value = false
    loadPlans()
  } catch (e) { ElMessage.error(e?.response?.data?.detail || '添加失败') }
}
async function deleteCourse(courseId) {
  try { await trainingApi.deletePlanCourse(courseId); ElMessage.success('已删除'); loadPlans() } catch {}
}

// ====== 毕业审核 ======
async function loadAudits() {
  auditLoading.value = true
  try {
    const res = await trainingApi.getAudits(auditMajor.value || undefined, auditGrade.value || undefined)
    audits.value = res.audits || []
  } finally { auditLoading.value = false }
}
async function runBatchAudit() {
  auditLoading.value = true
  try {
    const res = await trainingApi.auditBatch(auditMajor.value || undefined, auditGrade.value || undefined)
    ElMessage.success(`审核完成，共 ${res.total} 人`)
    loadAudits()
  } catch (e) { ElMessage.error('审核失败'); auditLoading.value = false }
}
async function reauditStudent(sid) {
  try { await trainingApi.auditStudent(sid); ElMessage.success(`${sid} 审核完成`); loadAudits() } catch {}
}

onMounted(async () => {
  await loadSchedules()
  try {
    const res = await getSelectionWindow()
    windowForm.value = { ...windowForm.value, ...res }
  } catch {}
})
</script>
