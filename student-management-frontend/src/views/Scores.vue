<template>
  <div style="padding:20px">
    <h2 style="margin-bottom:16px">我的成绩</h2>
    <el-skeleton :loading="loading" animated :count="3">
      <el-empty v-if="!scores.length" description="暂无成绩记录" />
      <template v-else>
        <div style="display:flex;gap:16px;margin-bottom:16px">
          <el-card style="flex:1;text-align:center">
            <div style="font-size:24px;color:#409eff;font-weight:bold">{{ avgGpa }}</div>
            <div style="color:#999;font-size:13px">平均绩点</div>
          </el-card>
          <el-card style="flex:1;text-align:center">
            <div style="font-size:24px;color:#67c23a;font-weight:bold">{{ totalCredits }}</div>
            <div style="color:#999;font-size:13px">已修学分</div>
          </el-card>
        </div>
        <el-table :data="scores" stripe>
          <el-table-column prop="course_name" label="课程名" />
          <el-table-column prop="credit" label="学分" />
          <el-table-column prop="score" label="平时成绩" />
          <el-table-column label="期末成绩">
            <template #default="{row}">
              {{ row.final_score ?? '待录入' }}
            </template>
          </el-table-column>
          <el-table-column label="总评绩点">
            <template #default="{row}">
              <span :style="{color: gpaColor(row.gpa), fontWeight:'bold'}">{{ row.total_gpa ?? '待录入' }}</span>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-skeleton>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getStudentScores } from '../api/score'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const scores = ref([])
const loading = ref(true)

const avgGpa = computed(() => {
  const totals = scores.value.filter(s => s.total_gpa != null)
  if (!totals.length) return '-'
  return (totals.reduce((s, c) => s + c.total_gpa, 0) / totals.length).toFixed(1)
})

const totalCredits = computed(() => scores.value.reduce((s, c) => s + (parseFloat(c.credit) || 0), 0).toFixed(1))

function gpaColor(v) {
  if (v >= 4.0) return '#67c23a'
  if (v >= 3.0) return '#409eff'
  if (v >= 2.0) return '#e6a23c'
  return v >= 1.0 ? '#f56c6c' : '#999'
}

onMounted(async () => {
  try {
    const res = await getStudentScores(authStore.userId)
    // 按课程分组展示
    const grouped = {}
    for (const s of res.scores || []) {
      if (!grouped[s.course_name]) grouped[s.course_name] = { course_name: s.course_name, credit: s.credit }
      if (s.score_type === '平时') grouped[s.course_name].score = s.score
      if (s.score_type === '期末') grouped[s.course_name].final_score = s.score
      if (s.score_type === '总评') grouped[s.course_name].total_gpa = s.gpa
    }
    scores.value = Object.values(grouped)
  } finally { loading.value = false }
})
</script>
