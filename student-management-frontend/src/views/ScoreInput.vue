<template>
  <div style="padding:20px">
    <h2 style="margin-bottom:16px">成绩录入</h2>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="手动录入" name="manual">
        <el-form inline>
          <el-form-item label="课程">
            <el-select v-model="manual.schedule_id" placeholder="选择课程" style="width:200px" @change="loadStudents">
              <el-option v-for="c in courses" :key="c.schedule_id" :label="c.course_name" :value="c.schedule_id" />
            </el-select>
          </el-form-item>
          <el-form-item label="类型">
            <el-select v-model="manual.score_type" style="width:120px">
              <el-option label="平时" value="平时" />
              <el-option label="期末" value="期末" />
            </el-select>
          </el-form-item>
        </el-form>
        <el-table :data="students" v-if="students.length" stripe style="margin-top:12px">
          <el-table-column prop="student_id" label="学号" />
          <el-table-column prop="student_name" label="姓名" />
          <el-table-column label="成绩">
            <template #default="{row}">
              <el-input-number v-model="row.score" :min="0" :max="100" size="small" />
            </template>
          </el-table-column>
        </el-table>
        <el-button v-if="students.length" type="primary" style="margin-top:12px" :loading="submitting" @click="submitManual">保存成绩</el-button>
      </el-tab-pane>
      <el-tab-pane label="Excel导入" name="import">
        <el-form-item label="课程">
          <el-select v-model="imp.schedule_id" placeholder="选择课程" style="width:200px">
            <el-option v-for="c in courses" :key="c.schedule_id" :label="c.course_name" :value="c.schedule_id" />
          </el-select>
        </el-form-item>
        <el-upload drag :auto-upload="false" :on-change="handleFile" accept=".xlsx" style="margin-top:12px">
          <el-icon><UploadFilled /></el-icon>
          <div>将Excel文件拖到此处或<em>点击上传</em></div>
        </el-upload>
        <el-button type="primary" style="margin-top:12px" :disabled="!fileReady" :loading="uploading" @click="submitImport">确认导入</el-button>
        <p v-if="importMsg" style="margin-top:8px;color:#67c23a">{{ importMsg }}</p>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { manualScore, importScores } from '../api/score'
import * as selectionApi from '../api/selection'

const activeTab = ref('manual')
const courses = ref([])
const students = ref([])
const submitting = ref(false)
const uploading = ref(false)
const fileReady = ref(false)
const importMsg = ref('')
const manual = ref({ schedule_id: null, score_type: '平时' })
const imp = ref({ schedule_id: null })
const selectedFile = ref(null)

async function loadCourses() {
  try {
    const res = await selectionApi.getMyCourses()
    const seen = new Set()
    courses.value = (res.courses || [])
      .filter(c => !seen.has(c.schedule_id) && seen.add(c.schedule_id))
      .map(c => ({ schedule_id: c.schedule_id, course_name: c.course_name }))
  } catch {}
}

async function loadStudents() {
  if (!manual.value.schedule_id) return
  try {
    const res = await selectionApi.getMyCourses()
    students.value = (res.courses || [])
      .filter(c => c.schedule_id === manual.value.schedule_id)
      .map(c => ({ student_id: c.student_id, student_name: c.student_name, score: null }))
  } catch {}
}

async function submitManual() {
  const data = students.value.filter(s => s.score != null).map(s => ({ student_id: s.student_id, score: s.score }))
  if (!data.length) { ElMessage.warning('请填写成绩'); return }
  submitting.value = true
  try {
    const res = await manualScore({ schedule_id: manual.value.schedule_id, score_type: manual.value.score_type, scores: data })
    ElMessage.success(`成功录入${res.inserted}条，更新${res.updated}条，计算${res.calculated}条总评`)
  } finally { submitting.value = false }
}

function handleFile(file) { selectedFile.value = file.raw; fileReady.value = true }
async function submitImport() {
  uploading.value = true; importMsg.value = ''
  try {
    const res = await importScores(imp.value.schedule_id, selectedFile.value)
    importMsg.value = `成功导入${res.success_count}条，计算${res.calculated}条总评`
    if (res.warnings?.length) importMsg.value += ' | ' + res.warnings.join(', ')
  } finally { uploading.value = false }
}

onMounted(loadCourses)
</script>
