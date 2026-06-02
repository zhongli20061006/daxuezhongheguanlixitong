<template>
  <div class="page-container">
    <h2 class="page-title">我的成绩</h2>
    <el-skeleton :loading="loading" animated :count="3">
      <template v-if="scores.length">
        <div class="stat-cards">
          <div class="stat-card"><div class="stat-icon" style="background:#EFF6FF">📊</div><div><div class="stat-value">{{ avgGpa }}</div><div class="stat-label">平均绩点</div></div></div>
          <div class="stat-card"><div class="stat-icon" style="background:#ECFDF5">📘</div><div><div class="stat-value">{{ totalCredits }}</div><div class="stat-label">已修学分</div></div></div>
        </div>
        <div class="content-card">
          <el-table :data="scores" stripe>
            <el-table-column prop="course_name" label="课程名" min-width="150" />
            <el-table-column prop="credit" label="学分" width="70" />
            <el-table-column label="平时成绩" width="80"><template #default="{row}">{{ row.score ?? '待录入' }}</template></el-table-column>
            <el-table-column label="期末成绩" width="80"><template #default="{row}">{{ row.final_score ?? '待录入' }}</template></el-table-column>
            <el-table-column label="总评绩点" width="100"><template #default="{row}"><span :style="{color:gpaColor(row.total_gpa),fontWeight:700}">{{ row.total_gpa ?? '待录入' }}</span></template></el-table-column>
          </el-table>
        </div>
      </template>
      <el-empty v-else description="暂无成绩记录" />
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
  const vals = scores.value.filter(s => s.total_gpa != null).map(s => s.total_gpa)
  return vals.length ? (vals.reduce((a,b)=>a+b,0)/vals.length).toFixed(1) : '-'
})
const totalCredits = computed(() => scores.value.reduce((s,c)=>s+(parseFloat(c.credit)||0),0).toFixed(1))

function gpaColor(v) { if(v==null)return '#9CA3AF'; if(v>=4.0)return '#059669'; if(v>=3.0)return '#2563EB'; if(v>=2.0)return '#D97706'; if(v>=1.0)return '#DC2626'; return '#6B7280' }

onMounted(async () => {
  try {
    const res = await getStudentScores(authStore.userId)
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
