<template>
  <div class="page-container">
    <h2 class="page-title">成绩录入</h2>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="手动录入" name="manual">
        <div class="content-card">
          <el-form inline>
            <el-form-item label="课程"><el-select v-model="manual.schedule_id" placeholder="选择课程" style="width:200px" @change="loadStudents"><el-option v-for="c in courses" :key="c.schedule_id" :label="c.course_name" :value="c.schedule_id" /></el-select></el-form-item>
            <el-form-item label="类型"><el-select v-model="manual.score_type" style="width:120px"><el-option label="平时" value="平时" /><el-option label="期末" value="期末" /></el-select></el-form-item>
          </el-form>
          <el-table v-if="students.length" :data="students" stripe>
            <el-table-column prop="student_id" label="学号" /><el-table-column prop="student_name" label="姓名" />
            <el-table-column label="成绩"><template #default="{row}"><el-input-number v-model="row.score" :min="0" :max="100" size="small" /></template></el-table-column>
          </el-table>
          <el-button v-if="students.length" type="primary" style="margin-top:12px" :loading="submitting" @click="submitManual">保存成绩</el-button>
        </div>
      </el-tab-pane>
      <el-tab-pane label="Excel导入" name="import">
        <div class="content-card">
          <el-form-item label="课程"><el-select v-model="imp.schedule_id" placeholder="选择课程" style="width:200px"><el-option v-for="c in courses" :key="c.schedule_id" :label="c.course_name" :value="c.schedule_id" /></el-select></el-form-item>
          <el-upload drag :auto-upload="false" :on-change="handleFile" accept=".xlsx" style="margin-top:12px">
            <div style="font-size:40px;margin-bottom:8px">📄</div>
            <div>将Excel文件拖到此处，或<em>点击上传</em></div>
          </el-upload>
          <el-button type="primary" style="margin-top:12px" :disabled="!fileReady" :loading="uploading" @click="submitImport">确认导入</el-button>
          <p v-if="importMsg" style="margin-top:8px;color:#059669">{{ importMsg }}</p>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { manualScore, importScores, getScoresBySchedule } from '../api/score'
import * as selectionApi from '../api/selection'

const activeTab = ref('manual')
const courses = ref([]); const students = ref([])
const submitting = ref(false); const uploading = ref(false); const fileReady = ref(false)
const importMsg = ref('')
const manual = ref({ schedule_id:null, score_type:'平时' })
const imp = ref({ schedule_id:null })
const selectedFile = ref(null)

async function loadCourses() { try { const r=await selectionApi.getMyCourses(); const s=new Set(); courses.value=(r.courses||[]).filter(c=>!s.has(c.schedule_id)&&s.add(c.schedule_id)).map(c=>({schedule_id:c.schedule_id,course_name:c.course_name})) } catch {} }
async function loadStudents() {
  if(!manual.value.schedule_id)return;
  try {
    const r=await selectionApi.getMyCourses();
    const list=(r.courses||[]).filter(c=>c.schedule_id===manual.value.schedule_id).map(c=>({student_id:c.student_id,student_name:c.student_name,score:null}));
    // 回填已有成绩
    try {
      const sr=await getScoresBySchedule(manual.value.schedule_id, manual.value.score_type);
      const scoreMap={};
      for(const s of (sr.scores||[])) if(s.score!=null) scoreMap[s.student_id]=s.score;
      for(const item of list) if(scoreMap[item.student_id]!=null) item.score=scoreMap[item.student_id];
    } catch{}
    students.value=list;
  } catch{}
}
async function submitManual() { const data=students.value.filter(s=>s.score!=null).map(s=>({student_id:s.student_id,score:s.score})); if(!data.length){ElMessage.warning('请填写成绩');return} submitting.value=true; try { const r=await manualScore({schedule_id:manual.value.schedule_id,score_type:manual.value.score_type,scores:data}); ElMessage.success(`成功录入${r.inserted}条，更新${r.updated}条`) } finally { submitting.value=false } }
function handleFile(file) { selectedFile.value=file.raw; fileReady.value=true }
async function submitImport() { uploading.value=true; importMsg.value=''; try { const r=await importScores(imp.value.schedule_id,selectedFile.value); importMsg.value=`成功导入${r.success_count}条`; if(r.warnings?.length) importMsg.value+=' | '+r.warnings.join(',') } finally { uploading.value=false } }
onMounted(loadCourses)
</script>
