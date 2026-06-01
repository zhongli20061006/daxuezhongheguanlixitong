<template>
  <div style="padding:20px">
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:16px">
      <h2>我的课表</h2>
      <el-tag type="primary">2024-2025-1</el-tag>
      <span>查看第</span>
      <el-select v-model="currentWeek" style="width:100px" @change="onWeekChange">
        <el-option v-for="w in 18" :key="w" :label="`第${w}周`" :value="w" />
      </el-select>
      <span>周</span>
    </div>
    <div style="display:flex;gap:8px;margin-bottom:12px">
      <span v-for="item in legend" :key="item.color" :style="{background:item.bg,color:item.color,border:`2px solid ${item.color}`,padding:'2px 8px',borderRadius:4,fontSize:12}">{{ item.text }}</span>
    </div>
    <el-skeleton :loading="loading" animated :count="5">
      <table class="schedule-grid" v-if="filteredCourses.length > 0">
        <thead><tr><th></th><th v-for="d in 7" :key="d">{{ weekdays[d-1] }}</th></tr></thead>
        <tbody>
          <tr v-for="(periodLabel, pi) in periodLabels" :key="pi">
            <td class="period-cell">{{ periodLabel }}</td>
            <td v-for="d in 7" :key="d" class="course-cell">
              <div v-for="c in getCellCourses(d, pi)" :key="c.id" :class="['course-card', c.course_type]" @click="showDetail(c)">
                <div class="course-name">{{ c.course_name }}</div>
                <div class="course-info">{{ c.teacher_name }}</div>
                <div class="course-info">{{ c.classroom_name }}</div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <el-empty v-else description="暂无课表数据" />
    </el-skeleton>
    <el-dialog :title="detail?.course_name" v-model="dialogVisible" width="400px">
      <div v-if="detail">
        <p><b>教师：</b>{{ detail.teacher_name }}</p>
        <p><b>教室：</b>{{ detail.classroom_name }}</p>
        <p><b>时间：</b> 周{{ detail.day_of_week }} {{ detail.period }}节</p>
        <p><b>周次：</b>{{ detail.weeks }}</p>
        <p><b>学分：</b>{{ detail.credit }}</p>
        <p><b>类型：</b>{{ typeMap[detail.course_type] || detail.course_type }}</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useScheduleStore } from '../stores/schedule'
import { isWeekInRange } from '../utils/weekParser'

const store = useScheduleStore()
const currentWeek = ref(1)
const dialogVisible = ref(false)
const detail = ref(null)
const weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const periodLabels = ['1-2', '3-4', '5-6', '7-8', '9-10']
const legend = [
  { text: '必修', bg: '#e6f0ff', color: '#409eff' },
  { text: '限选', bg: '#fff3e6', color: '#e6a23c' },
  { text: '选修', bg: '#e6ffe6', color: '#67c23a' }
]
const typeMap = { compulsory: '必修', limited: '限选', elective: '选修' }

const allCourses = computed(() => {
  const arr = []
  for (const day in store.weeklyCourses) {
    for (const c of store.weeklyCourses[day]) arr.push(c)
  }
  return arr
})

const filteredCourses = computed(() => allCourses.value.filter(c => isWeekInRange(currentWeek.value, c.weeks)))

const loading = computed(() => store.loading)

function getCellCourses(day, periodIdx) {
  const period = periodLabels[periodIdx] || ''
  return filteredCourses.value.filter(c => c.day_of_week === day && c.period === period)
}

function showDetail(c) { detail.value = c; dialogVisible.value = true }
function onWeekChange() {}

onMounted(() => store.fetchMySchedule())
</script>

<style scoped>
.schedule-grid { width:100%; border-collapse:collapse; }
.schedule-grid th, .schedule-grid td { border:1px solid #ddd; padding:4px; vertical-align:top; text-align:center; }
.schedule-grid th { background:#f0f0f0; height:36px; }
.course-cell { width:13%; min-height:60px; }
.period-cell { width:60px; background:#fafafa; font-size:12px; color:#666; }
.course-card { margin:2px 0; padding:4px 6px; border-radius:4px; border-left:3px solid; cursor:pointer; font-size:12px; }
.course-card.compulsory { background:#e6f0ff; border-color:#409eff; }
.course-card.limited { background:#fff3e6; border-color:#e6a23c; }
.course-card.elective { background:#e6ffe6; border-color:#67c23a; }
.course-name { font-weight:bold; font-size:12px; }
.course-info { color:#666; font-size:11px; }
</style>
