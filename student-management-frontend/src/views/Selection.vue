<template>
  <div style="padding:20px">
    <h2 style="margin-bottom:16px">选课中心</h2>
    <el-tabs v-model="activeTab">
      <!-- 可选课程 -->
      <el-tab-pane label="可选课程" name="available">
        <div style="display:flex;gap:12px;margin-bottom:16px;align-items:center">
          <el-select v-model="typeFilter" placeholder="课程类型" clearable style="width:140px">
            <el-option label="全部" value="" />
            <el-option label="限选" value="limited" />
            <el-option label="选修" value="elective" />
          </el-select>
          <el-input v-model="searchKeyword" placeholder="搜索课程名" clearable style="width:200px" />
          <el-tag type="success">已选学分：{{ selectionStore.selectedCredits }}</el-tag>
        </div>
        <el-skeleton :loading="selectionStore.availLoading" animated :count="3">
          <div v-if="filteredCourses.length" class="course-grid">
            <el-card v-for="c in filteredCourses" :key="c.schedule_id" class="course-card-item">
              <div class="card-header">
                <el-tag :type="typeTag(c.course_type)" size="small">{{ typeMap[c.course_type] }}</el-tag>
                <span class="course-title">{{ c.course_name }}</span>
              </div>
              <div class="card-body">
                <p>学分：{{ c.credit }} | 教师：{{ c.teacher_name }}</p>
                <p>时间：周{{ c.day_of_week }} {{ c.period }}节 | {{ c.classroom_name }}</p>
                <p>周次：{{ c.weeks }}</p>
                <el-progress :percentage="capacityPct(c)" :stroke-width="8" :color="c.enrolled >= c.capacity ? '#f56c6c' : '#409eff'" />
                <span style="font-size:12px;color:#999">{{ c.enrolled }}/{{ c.capacity }}</span>
              </div>
              <div class="card-footer">
                <el-button v-if="c.selected" type="success" disabled>已选</el-button>
                <el-button v-else-if="c.enrolled >= c.capacity" type="info" disabled>名额已满</el-button>
                <el-button v-else type="primary" :loading="enrollingId === c.schedule_id" @click="handleEnroll(c)">选课</el-button>
              </div>
            </el-card>
          </div>
          <el-empty v-else description="暂无可选课程" />
        </el-skeleton>
      </el-tab-pane>
      <!-- 我的已选 -->
      <el-tab-pane label="我的已选" name="selected">
        <el-tag type="success" style="margin-bottom:12px">已选学分：{{ selectionStore.selectedCredits }}</el-tag>
        <el-table :data="selectionStore.myCourses" v-loading="selectionStore.loading" empty-text="暂未选课" stripe>
          <el-table-column prop="course_name" label="课程名" />
          <el-table-column prop="teacher_name" label="教师" />
          <el-table-column label="时间">
            <template #default="{row}"> 周{{ row.day_of_week }} {{ row.period }}节 </template>
          </el-table-column>
          <el-table-column prop="classroom_name" label="教室" />
          <el-table-column prop="credit" label="学分" />
          <el-table-column label="类型">
            <template #default="{row}">
              <el-tag :type="typeTag(row.course_type)" size="small">{{ typeMap[row.course_type] }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{row}">
              <el-button type="danger" size="small" :loading="droppingId === row.schedule_id" @click="handleDrop(row)">退课</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useSelectionStore } from '../stores/selection'

const selectionStore = useSelectionStore()
const activeTab = ref('available')
const typeFilter = ref('')
const searchKeyword = ref('')
const enrollingId = ref(null)
const droppingId = ref(null)
const typeMap = { compulsory: '必修', limited: '限选', elective: '选修' }

const filteredCourses = computed(() => {
  let list = selectionStore.availableCourses
  if (typeFilter.value) list = list.filter(c => c.course_type === typeFilter.value)
  if (searchKeyword.value) list = list.filter(c => c.course_name.includes(searchKeyword.value))
  return list
})

function typeTag(t) {
  return { compulsory: 'danger', limited: 'warning', elective: 'success' }[t] || 'info'
}

function capacityPct(c) {
  if (!c.capacity) return 0
  return Math.round(c.enrolled / c.capacity * 100)
}

async function handleEnroll(course) {
  enrollingId.value = course.schedule_id
  try {
    await selectionStore.enroll(course.schedule_id)
    ElMessage.success('选课成功')
  } catch { /* handled by interceptor */ }
  finally { enrollingId.value = null }
}

async function handleDrop(row) {
  try {
    await ElMessageBox.confirm('确定要退选该课程吗？', '确认退课', { type: 'warning' })
    droppingId.value = row.schedule_id
    await selectionStore.drop(row.schedule_id)
    ElMessage.success('退课成功')
  } catch { /* cancelled or error */ }
  finally { droppingId.value = null }
}

onMounted(async () => {
  await Promise.all([
    selectionStore.fetchAvailableCourses(),
    selectionStore.fetchMyCourses()
  ])
})
</script>

<style scoped>
.course-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:16px; }
.card-header { display:flex; align-items:center; gap:8px; margin-bottom:8px; }
.course-title { font-weight:bold; font-size:15px; }
.card-body p { margin:4px 0; font-size:13px; color:#666; }
.card-footer { margin-top:12px; text-align:right; }
</style>
