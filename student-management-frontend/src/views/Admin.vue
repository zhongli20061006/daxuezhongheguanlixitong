<template>
  <div class="page-container">
    <h2 class="page-title">管理后台</h2>
    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <el-tab-pane label="课表管理" name="schedule">
        <div class="content-card">
          <div style="display:flex;gap:12px;margin-bottom:12px;align-items:center"><el-select v-model="adminClassId" placeholder="选择班级" style="width:200px" @change="loadSchedules"><el-option v-for="c in classOptions" :key="c" :label="`班级${c}`" :value="c" /></el-select><el-button type="primary" @click="showScheduleDialog(null)">新增排课</el-button></div>
          <el-table :data="schedules" v-loading="schLoading" stripe><el-table-column prop="id" label="ID" width="60" /><el-table-column prop="course_name" label="课程" /><el-table-column prop="teacher_name" label="教师" /><el-table-column prop="classroom_name" label="教室" /><el-table-column label="时间"><template #default="{row}">周{{ row.day_of_week }} {{ row.period }}节</template></el-table-column><el-table-column prop="weeks" label="周次" /><el-table-column label="操作" width="150"><template #default="{row}"><el-button size="small" @click="showScheduleDialog(row)">编辑</el-button><el-button size="small" type="danger" @click="deleteSch(row)">删除</el-button></template></el-table-column></el-table>
        </div>
      </el-tab-pane>
      <el-tab-pane label="选课设置" name="window">
        <div class="content-card" style="max-width:500px">
          <el-form :model="windowForm" label-width="120px"><el-form-item label="选课开始"><el-input v-model="windowForm.selection_start_time" placeholder="YYYY-MM-DD HH:MM:SS" /></el-form-item><el-form-item label="选课结束"><el-input v-model="windowForm.selection_end_time" /></el-form-item><el-form-item label="退课截止"><el-input v-model="windowForm.drop_deadline" /></el-form-item><el-form-item><el-button type="primary" @click="saveWindow">保存</el-button></el-form-item></el-form>
        </div>
      </el-tab-pane>
      <el-tab-pane label="用户管理" name="users">
        <div class="content-card">
          <el-table :data="users" v-loading="userLoading" stripe><el-table-column prop="username" label="用户名" /><el-table-column label="角色"><template #default="{row}"><el-tag size="small">{{ row.role }}</el-tag></template></el-table-column><el-table-column prop="role_id" label="角色ID" /><el-table-column prop="created_at" label="创建时间" width="160" /><el-table-column label="操作" width="120"><template #default="{row}"><el-button size="small" type="warning" @click="resetPwd(row)">重置密码</el-button></template></el-table-column></el-table>
        </div>
      </el-tab-pane>
      <el-tab-pane label="培养方案" name="plans">
        <div class="content-card">
          <el-button type="primary" @click="showPlanDialog" style="margin-bottom:12px">新增方案</el-button>
          <el-table :data="plans" v-loading="planLoading" stripe @expand-change="onPlanExpand"><el-table-column type="expand"><template #default="{row}"><div style="padding:8px 20px"><el-button size="small" type="primary" @click="showAddCourseDialog(row)">添加课程</el-button><el-table :data="row._courses||[]" size="small" border style="margin-top:8px"><el-table-column prop="subject_name" label="课程名" /><el-table-column prop="credit" label="学分" width="70" /><el-table-column label="类型" width="70"><template #default="{r}"><el-tag :type="r.course_type==='limited'?'warning':r.course_type==='elective'?'success':''" size="small">{{ typeMap2[r.course_type] }}</el-tag></template></el-table-column><el-table-column prop="limited_group" label="分组" width="100" /><el-table-column prop="min_required" label="至少选" width="60" /><el-table-column label="操作" width="80"><template #default="{r}"><el-button size="small" type="danger" @click="deleteCourse(r.id)">删除</el-button></template></el-table-column></el-table></div></template></el-table-column><el-table-column prop="id" label="ID" width="60" /><el-table-column prop="major" label="专业" /><el-table-column prop="grade" label="年级" width="80" /><el-table-column prop="total_credits_required" label="总学分" width="80" /><el-table-column prop="elective_credits_required" label="选修" width="80" /></el-table>
        </div>
      </el-tab-pane>
      <el-tab-pane label="毕业审核" name="audit">
        <div class="content-card">
          <div style="display:flex;gap:12px;margin-bottom:12px;align-items:center"><el-input v-model="auditMajor" placeholder="专业筛选" style="width:180px" clearable /><el-input-number v-model="auditGrade" placeholder="年级" :min="2000" style="width:120px" /><el-button type="primary" @click="loadAudits">查询</el-button><el-button type="success" @click="runBatchAudit">批量审核</el-button></div>
          <el-table :data="audits" v-loading="auditLoading" stripe>... </el-table>
        </div>
      </el-tab-pane>
      <el-tab-pane label="考试管理" name="exam">
        <div class="content-card">
          <el-button type="primary" @click="generateExams" :loading="examGenerating" style="margin-bottom:12px">自动排考</el-button>
          <el-table :data="examList" v-loading="examLoading" stripe>
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="subject_name" label="科目" />
            <el-table-column prop="classroom_name" label="教室" />
            <el-table-column label="时间"><template #default="{row}">{{ row.date }} {{ row.start_time }}-{{ row.end_time }}</template></el-table-column>
            <el-table-column prop="invigilator_name" label="监考教师" />
            <el-table-column label="状态" width="80"><template #default="{row}"><el-tag :type="row.status==='已发布'?'success':row.status==='已排考'?'warning':'info'" size="small">{{ row.status }}</el-tag></template></el-table-column>
            <el-table-column label="操作" width="80"><template #default="{row}"><el-button v-if="row.status==='已排考'" size="small" type="success" @click="publishHandler(row.id)">发布</el-button></template></el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>
    <!-- Dialogs -->
    <el-dialog v-model="schDialogVisible" :title="schEdit.id?'编辑排课':'新增排课'" width="500px"><el-form :model="schEdit" label-width="80px"><el-form-item label="教师ID"><el-input-number v-model="schEdit.teacher_id" /></el-form-item><el-form-item label="科目ID"><el-input-number v-model="schEdit.subject_id" /></el-form-item><el-form-item label="班级ID"><el-input-number v-model="schEdit.class_id" /></el-form-item><el-form-item label="教室ID"><el-input-number v-model="schEdit.classroom_id" /></el-form-item><el-form-item label="星期"><el-input-number v-model="schEdit.day_of_week" :min="1" :max="7" /></el-form-item><el-form-item label="节次"><el-input v-model="schEdit.period" placeholder="1-2" /></el-form-item><el-form-item label="周次"><el-input v-model="schEdit.weeks" placeholder="1-18" /></el-form-item><el-form-item label="学期"><el-input v-model="schEdit.semester" placeholder="2024-2025-1" /></el-form-item></el-form><template #footer><el-button @click="schDialogVisible=false">取消</el-button><el-button type="primary" @click="saveSchedule">保存</el-button></template></el-dialog>
    <el-dialog v-model="planDialogVisible" title="新增培养方案" width="400px"><el-form :model="planForm" label-width="100px"><el-form-item label="专业"><el-input v-model="planForm.major" /></el-form-item><el-form-item label="年级"><el-input-number v-model="planForm.grade" :min="2000" /></el-form-item><el-form-item label="总学分"><el-input-number v-model="planForm.total_credits_required" :min="1" :precision="1" /></el-form-item><el-form-item label="选修学分"><el-input-number v-model="planForm.elective_credits_required" :min="0" :precision="1" /></el-form-item></el-form><template #footer><el-button @click="planDialogVisible=false">取消</el-button><el-button type="primary" @click="createPlan">保存</el-button></template></el-dialog>
    <el-dialog v-model="courseDialogVisible" title="添加方案课程" width="400px"><el-form :model="courseForm" label-width="100px"><el-form-item label="科目ID"><el-input-number v-model="courseForm.subject_id" /></el-form-item><el-form-item label="类型"><el-select v-model="courseForm.course_type"><el-option label="必修" value="compulsory" /><el-option label="限选" value="limited" /><el-option label="选修" value="elective" /></el-select></el-form-item><el-form-item label="学分"><el-input-number v-model="courseForm.credit" :min="0" :precision="1" /></el-form-item><el-form-item label="限选组"><el-input v-model="courseForm.limited_group" /></el-form-item><el-form-item label="至少选"><el-input-number v-model="courseForm.min_required" :min="1" /></el-form-item></el-form><template #footer><el-button @click="courseDialogVisible=false">取消</el-button><el-button type="primary" @click="addCourse">确定</el-button></template></el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as scheduleApi from '../api/schedule'
import { setSelectionWindow, getSelectionWindow, getUsers, resetPassword } from '../api/admin'
import * as trainingApi from '../api/training'
import * as examApi from '../api/exam'
const activeTab=ref('schedule'); const adminClassId=ref(1); const classOptions=[1,2,3]; const schedules=ref([]); const schLoading=ref(false); const schDialogVisible=ref(false); const schEdit=ref({})
const windowForm=ref({selection_start_time:'',selection_end_time:'',drop_deadline:''})
const users=ref([]); const userLoading=ref(false)
const typeMap2={compulsory:'必修',limited:'限选',elective:'选修'}
const plans=ref([]); const planLoading=ref(false); const planDialogVisible=ref(false); const planForm=ref({major:'',grade:2024,total_credits_required:150,elective_credits_required:20})
const courseDialogVisible=ref(false); const courseForm=ref({subject_id:null,course_type:'compulsory',credit:3,limited_group:'',min_required:2}); let selectedPlanId=null
const audits=ref([]); const auditLoading=ref(false); const auditMajor=ref(''); const auditGrade=ref(null)
// 考试管理
const examList=ref([]); const examLoading=ref(false); const examGenerating=ref(false)
async function loadSchedules(){schLoading.value=true;try{const r=await scheduleApi.getClassSchedule(adminClassId.value);schedules.value=r.schedules||[]}finally{schLoading.value=false}}
function showScheduleDialog(r){schEdit.value=r?{...r}:{teacher_id:null,subject_id:null,class_id:1,classroom_id:null,day_of_week:1,period:'1-2',weeks:'1-18',semester:'2024-2025-1'};schDialogVisible.value=true}
async function saveSchedule(){try{if(schEdit.value.id){await scheduleApi.updateSchedule(schEdit.value.id,schEdit.value)}else{await scheduleApi.createSchedule(schEdit.value)}ElMessage.success('保存成功');schDialogVisible.value=false;loadSchedules()}catch(e){ElMessage.error(e?.response?.data?.detail||'保存失败')}}
async function deleteSch(r){try{await ElMessageBox.confirm('确定删除？','确认');await scheduleApi.deleteSchedule(r.id);ElMessage.success('已删除');loadSchedules()}catch{}}
async function saveWindow(){await setSelectionWindow(windowForm.value);ElMessage.success('保存成功')}
async function loadUsers(){userLoading.value=true;try{const r=await getUsers();users.value=r.users||[]}finally{userLoading.value=false}}
async function resetPwd(r){try{const chars='ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789';const a=new Uint8Array(8);crypto.getRandomValues(a);const p=Array.from(a).map(b=>chars[b%chars.length]).join('');await ElMessageBox.confirm(`确定重置 ${r.username} 的密码为 ${p}？`,'确认');await resetPassword(r.id,p);ElMessage.success(`密码已重置为: ${p}`)}catch{}}
function onTabChange(t){if(t==='users')loadUsers();if(t==='plans')loadPlans();if(t==='audit')loadAudits();if(t==='exam')loadExams()}
async function loadPlans(){planLoading.value=true;try{const r=await trainingApi.getPlans();plans.value=(r.plans||[]).map(p=>({...p,_courses:[]}))}finally{planLoading.value=false}}
async function onPlanExpand(r){if(r._courses.length)return;try{const res=await trainingApi.getPlanCourses(r.id);r._courses=res.courses||[]}catch{}}
function showPlanDialog(){planForm.value={major:'',grade:2024,total_credits_required:150,elective_credits_required:20};planDialogVisible.value=true}
async function createPlan(){try{await trainingApi.createPlan(planForm.value);ElMessage.success('方案已创建');planDialogVisible.value=false;loadPlans()}catch(e){ElMessage.error(e?.response?.data?.detail||'创建失败')}}
function showAddCourseDialog(r){selectedPlanId=r.id;courseForm.value={subject_id:null,course_type:'compulsory',credit:3,limited_group:'',min_required:null};courseDialogVisible.value=true}
async function addCourse(){try{await trainingApi.addPlanCourse({...courseForm.value,plan_id:selectedPlanId});ElMessage.success('课程已添加');courseDialogVisible.value=false;loadPlans()}catch(e){ElMessage.error(e?.response?.data?.detail||'添加失败')}}
async function deleteCourse(id){try{await trainingApi.deletePlanCourse(id);ElMessage.success('已删除');loadPlans()}catch{}}
async function loadAudits(){auditLoading.value=true;try{const r=await trainingApi.getAudits(auditMajor.value||undefined,auditGrade.value||undefined);audits.value=r.audits||[]}finally{auditLoading.value=false}}
async function runBatchAudit(){auditLoading.value=true;try{const r=await trainingApi.auditBatch(auditMajor.value||undefined,auditGrade.value||undefined);ElMessage.success(`审核完成，共 ${r.total} 人`);loadAudits()}catch(e){ElMessage.error('审核失败');auditLoading.value=false}}
async function reauditStudent(sid){try{await trainingApi.auditStudent(sid);ElMessage.success(`${sid} 审核完成`);loadAudits()}catch{}}
async function loadExams(){examLoading.value=true;try{const r=await examApi.listExams();examList.value=r.exams||[]}finally{examLoading.value=false}}
async function generateExams(){examGenerating.value=true;try{const r=await examApi.generateExams();ElMessage.success(r.message);loadExams()}catch(e){ElMessage.error(e?.response?.data?.detail||'排考失败')}finally{examGenerating.value=false}}
async function publishHandler(id){try{await examApi.publishExam(id);ElMessage.success('已发布');loadExams()}catch{}}
onMounted(async()=>{await loadSchedules();try{const r=await getSelectionWindow();windowForm.value={...windowForm.value,...r}}catch{}})
</script>
