<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-header-icon" style="background:var(--color-primary-bg);color:var(--color-primary)">📅</div>
      <div>
        <h2 class="page-title" style="margin:0">我的课表</h2>
        <div class="page-subtitle">查看本周课程安排与上课信息</div>
      </div>
    </div>
    <div class="content-card card-accent">
      <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:16px">
        <h2 class="page-title" style="margin-bottom:0;flex:1;font-size:18px">第{{ currentWeek }}周 课程表</h2>
        <el-tag type="primary">2024-2025-1</el-tag>
        <el-button text circle @click="prevWeek" :disabled="currentWeek <= 1">◀</el-button>
        <el-select v-model="currentWeek" style="width:100px" @change="onWeekChange">
          <el-option v-for="w in 18" :key="w" :label="`第${w}周`" :value="w" />
        </el-select>
        <el-button text circle @click="nextWeek" :disabled="currentWeek >= 18">▶</el-button>
        <span style="margin:0 8px;font-size:13px;color:#999">|</span>
        <span v-for="item in legend" :key="item.text" :style="{background:item.bg,color:item.color,border:`2px solid ${item.color}`,padding:'2px 10px',borderRadius:4,fontSize:12}">{{ item.text }}</span>
      </div>
      <el-skeleton :loading="store.loading" animated :count="5">
        <div v-if="filteredCourses.length" class="schedule-grid-wrap">
          <table class="schedule-grid">
            <thead><tr><th style="width:70px"></th><th v-for="d in 7" :key="d">{{ weekdays[d-1] }}</th></tr></thead>
            <tbody>
              <tr v-for="(pl, pi) in periodLabels" :key="pi">
                <td class="period-cell">{{ pl }}节</td>
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
        </div>
        <el-empty v-else description="暂无课表数据" :image-size="80" />
      </el-skeleton>
    </div>
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
const weekdays = ['周一','周二','周三','周四','周五','周六','周日']
const periodLabels = ['1-2','3-4','5-6','7-8','9-10']
const typeMap = { compulsory:'必修', limited:'限选', elective:'选修' }
const legend = [
  { text:'必修', bg:'#EFF6FF', color:'#2563EB' }, { text:'限选', bg:'#FFFBEB', color:'#D97706' },
  { text:'选修', bg:'#ECFDF5', color:'#059669' },
]

const allCourses = computed(() => {
  const arr = []
  for (const day in store.weeklyCourses)
    for (const c of store.weeklyCourses[day]) arr.push(c)
  return arr
})
const filteredCourses = computed(() => allCourses.value.filter(c => isWeekInRange(currentWeek.value, c.weeks)))
function getCellCourses(day, pi) { const p = periodLabels[pi]; return filteredCourses.value.filter(c => c.day_of_week === day && c.period === p) }
function showDetail(c) { detail.value = c; dialogVisible.value = true }
function onWeekChange() {}
function prevWeek() { if (currentWeek.value > 1) currentWeek.value-- }
function nextWeek() { if (currentWeek.value < 18) currentWeek.value++ }

onMounted(() => store.fetchMySchedule())
</script>

<style scoped>
.schedule-grid-wrap { overflow-x:auto; }
.schedule-grid { width:100%; border-collapse:collapse; min-width:700px; }
.schedule-grid th, .schedule-grid td { border:1px solid #E5E7EB; padding:4px; vertical-align:top; text-align:center; }
.schedule-grid th { background:#F3F4F6; height:40px; font-weight:600; font-size:13px; }
.course-cell { width:13%; min-height:90px; background:#fff; }
.period-cell { width:70px; background:#F9FAFB; font-size:12px; color:#6B7280; }
.course-card { margin:3px 0; padding:6px 8px; border-radius:6px; border-left:4px solid; cursor:pointer; font-size:12px; transition:box-shadow .15s; }
.course-card:hover { box-shadow:0 2px 8px rgba(0,0,0,.1); }
.course-card.compulsory { background:#EFF6FF; border-color:#2563EB; }
.course-card.limited { background:#FFFBEB; border-color:#D97706; }
.course-card.elective { background:#ECFDF5; border-color:#059669; }
.course-name { font-weight:600; font-size:13px; }
.course-info { color:#6B7280; font-size:11px; }
@media (max-width:768px) { .course-cell { min-height:60px; } }
</style>
