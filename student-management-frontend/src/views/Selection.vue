<template>
  <div class="page-container">
    <h2 class="page-title">选课中心</h2>
    <div class="stat-cards">
      <div class="stat-card"><div class="stat-icon" style="background:#EFF6FF">📘</div><div><div class="stat-value">{{ selectionStore.selectedCredits }}</div><div class="stat-label">已选学分</div></div></div>
      <div class="stat-card"><div class="stat-icon" style="background:#ECFDF5">📚</div><div><div class="stat-value">{{ availableCount }}</div><div class="stat-label">可选课程</div></div></div>
      <div class="stat-card"><div class="stat-icon" style="background:#FFFBEB">✅</div><div><div class="stat-value">{{ selectionStore.myCourses.length }}</div><div class="stat-label">已选课程</div></div></div>
    </div>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="可选课程" name="available">
        <div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;align-items:center">
          <el-select v-model="typeFilter" placeholder="课程类型" clearable style="width:140px">
            <el-option label="全部" value="" /><el-option label="限选" value="limited" /><el-option label="选修" value="elective" />
          </el-select>
          <el-input v-model="searchKeyword" placeholder="搜索课程名" clearable style="width:200px" />
        </div>
        <el-skeleton :loading="selectionStore.availLoading" animated :count="3">
          <div v-if="filteredCourses.length">
            <div v-for="c in filteredCourses" :key="c.schedule_id" :class="['course-card-item', { selected: c.selected }]">
              <div class="card-row1">
                <el-tag :type="c.course_type==='limited'?'warning':'success'" size="small">{{ typeMap[c.course_type] }}</el-tag>
                <span class="course-title">{{ c.course_name }}</span>
                <span style="margin-left:auto;color:#6B7280;font-size:13px">{{ c.credit }} 学分</span>
              </div>
              <div class="card-row2">
                <span>👤 {{ c.teacher_name }}</span><span>🕐 周{{ c.day_of_week }} {{ c.period }}节</span><span>🏫 {{ c.classroom_name }}</span>
              </div>
              <div class="card-row3"><span>📅 {{ c.weeks }}周</span></div>
              <div class="card-row4">
                <el-progress :percentage="capacityPct(c)" :stroke-width="6" :color="c.enrolled >= c.capacity ? '#DC2626' : '#2563EB'" style="flex:1;margin-right:12px" />
                <span style="font-size:12px;color:#6B7280;margin-right:12px">{{ c.enrolled }}/{{ c.capacity }}</span>
                <el-button v-if="c.selected" type="success" disabled size="small">已选</el-button>
                <el-button v-else-if="c.enrolled >= c.capacity" type="info" disabled size="small">名额已满</el-button>
                <el-button v-else type="primary" :loading="enrollingId===c.schedule_id" size="small" @click="handleEnroll(c)">选课</el-button>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无可选课程" />
        </el-skeleton>
      </el-tab-pane>
      <el-tab-pane label="我的已选" name="selected">
        <el-table :data="selectionStore.myCourses" v-loading="selectionStore.loading" stripe empty-text="暂未选课">
          <el-table-column prop="course_name" label="课程名" />
          <el-table-column prop="teacher_name" label="教师" />
          <el-table-column label="时间"><template #default="{row}"> 周{{ row.day_of_week }} {{ row.period }}节 </template></el-table-column>
          <el-table-column prop="classroom_name" label="教室" />
          <el-table-column prop="credit" label="学分" width="70" />
          <el-table-column label="类型" width="80"><template #default="{row}"><el-tag :type="row.course_type==='limited'?'warning':'success'" size="small">{{ typeMap[row.course_type] }}</el-tag></template></el-table-column>
          <el-table-column label="操作" width="100"><template #default="{row}"><el-button type="danger" size="small" :loading="droppingId===row.schedule_id" @click="handleDrop(row)">退课</el-button></template></el-table-column>
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
const enrollingId = ref(null); const droppingId = ref(null)
const typeMap = { compulsory:'必修', limited:'限选', elective:'选修' }

const filteredCourses = computed(() => {
  let list = selectionStore.availableCourses
  if (typeFilter.value) list = list.filter(c => c.course_type === typeFilter.value)
  if (searchKeyword.value) list = list.filter(c => c.course_name.includes(searchKeyword.value))
  return list
})
const availableCount = computed(() => selectionStore.availableCourses.length)

function capacityPct(c) { return c.capacity ? Math.round(c.enrolled / c.capacity * 100) : 0 }

async function handleEnroll(c) {
  enrollingId.value = c.schedule_id
  try { await selectionStore.enroll(c.schedule_id); ElMessage.success('选课成功') } catch {}
  finally { enrollingId.value = null }
}
async function handleDrop(row) {
  try { await ElMessageBox.confirm('确定要退选该课程吗？', '确认退课', { type:'warning' }); droppingId.value = row.schedule_id; await selectionStore.drop(row.schedule_id); ElMessage.success('退课成功') }
  catch {} finally { droppingId.value = null }
}

onMounted(() => { selectionStore.fetchAvailableCourses(); selectionStore.fetchMyCourses() })
</script>

<style scoped>
.course-card-item { background:#fff; border-radius:8px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,.08); margin-bottom:12px; transition:all .2s; }
.course-card-item.selected { background:#F0FDF4; border-left:4px solid #059669; }
.card-row1 { display:flex; align-items:center; gap:8px; margin-bottom:8px; }
.card-row2 { display:flex; gap:16px; font-size:13px; color:#6B7280; margin-bottom:4px; flex-wrap:wrap; }
.card-row3 { font-size:12px; color:#9CA3AF; margin-bottom:8px; }
.card-row4 { display:flex; align-items:center; }
.course-title { font-size:16px; font-weight:600; }
</style>
