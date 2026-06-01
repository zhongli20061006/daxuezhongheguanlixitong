<template>
  <table class="schedule-table">
    <thead>
      <tr>
        <th class="time-col">节次</th>
        <th v-for="d in days" :key="d">周{{ d }}</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="row in timeSlots" :key="row.label">
        <td class="time-col">{{ row.label }}<br><small>{{ row.time }}</small></td>
        <td v-for="d in days" :key="d" class="cell">
          <div v-if="getCourse(d, row.start, row.end)" class="course-card" :class="'type-' + getCourse(d, row.start, row.end).course_type" @click="$emit('select', getCourse(d, row.start, row.end))">
            <div class="course-name">{{ getCourse(d, row.start, row.end).course_name }}</div>
            <div class="course-info">{{ getCourse(d, row.start, row.end).teacher_name }}</div>
            <div class="course-info">{{ getCourse(d, row.start, row.end).classroom_name }}</div>
          </div>
        </td>
      </tr>
    </tbody>
  </table>
</template>

<script setup>
import { parsePeriod } from '@/utils/periodParser'

const props = defineProps({ courses: { type: Array, default: () => [] }, currentWeek: { type: Number, default: 1 } })
defineEmits(['select'])

const days = [1, 2, 3, 4, 5, 6, 7]
const timeSlots = [
  { label: '第1-2节', time: '08:00-09:35', start: 1, end: 2 },
  { label: '第3-4节', time: '10:00-11:35', start: 3, end: 4 },
  { label: '第5-6节', time: '14:00-15:35', start: 5, end: 6 },
  { label: '第7-8节', time: '16:00-17:35', start: 7, end: 8 },
  { label: '第9-10节', time: '19:00-20:35', start: 9, end: 10 },
]

function getCourse(day, slotStart, slotEnd) {
  return props.courses.find(c => {
    if (c.day_of_week !== day) return false
    try {
      const p = parsePeriod(c.period)
      return p.start >= slotStart && p.start <= slotEnd
    } catch { return false }
  }) || null
}
</script>

<style scoped>
.schedule-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.schedule-table th, .schedule-table td { border: 1px solid #e0e0e0; padding: 4px; vertical-align: top; }
.time-col { width: 80px; text-align: center; background: #f5f7fa; font-size: 12px; }
.cell { height: 70px; min-width: 100px; }
.course-card { padding: 4px 6px; border-radius: 4px; cursor: pointer; border-left: 3px solid; font-size: 12px; }
.course-name { font-weight: bold; }
.course-info { color: #666; font-size: 11px; }
.type-compulsory { background: #ecf5ff; border-color: #409eff; }
.type-limited { background: #fdf6ec; border-color: #e6a23c; }
.type-elective { background: #f0f9eb; border-color: #67c23a; }
</style>
