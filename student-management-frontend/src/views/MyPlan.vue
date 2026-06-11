<template>
  <div class="page">
    <h2>培养方案</h2>
    <el-empty v-if="!plan" description="未找到匹配的培养方案" />
    <template v-else>
      <el-card style="margin-bottom:16px">
        <el-descriptions :column="3" border>
          <el-descriptions-item label="专业">{{ plan.major }}</el-descriptions-item>
          <el-descriptions-item label="年级">{{ plan.grade }}级</el-descriptions-item>
          <el-descriptions-item label="总学分">
            {{ plan.total_credits_earned }}/{{ plan.total_credits_required }}
          </el-descriptions-item>
          <el-descriptions-item label="必修学分">已获 {{ plan.total_credits_earned }}</el-descriptions-item>
          <el-descriptions-item label="选修学分">
            {{ plan.elective_credits_earned }}/{{ plan.elective_credits_required }}
          </el-descriptions-item>
          <el-descriptions-item label="毕业审核">
            <el-tag v-if="audit" :type="audit.is_graduatable ? 'success' : 'danger'">
              {{ audit.is_graduatable ? '可毕业' : '未达标' }}
            </el-tag>
            <el-tag v-else type="info">未审核</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <h3 style="margin-bottom:12px">课程列表</h3>
      <el-table :data="courses" border stripe v-loading="loading" empty-text="无课程数据">
        <el-table-column prop="subject_name" label="课程名" min-width="150" />
        <el-table-column prop="credit" label="学分" width="70" />
        <el-table-column label="类型" width="90">
          <template #default="{ row }">
            <el-tag :type="typeTag(row.course_type)" size="small">{{ typeMap[row.course_type] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="limited_group" label="分组" width="120" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="gpa" label="绩点" width="70">
          <template #default="{ row }">{{ row.gpa ?? '-' }}</template>
        </el-table-column>
      </el-table>

      <el-divider />
      <h3 style="margin-bottom:12px">限选分组进度</h3>
      <el-empty v-if="!groups.length" description="无限选课要求" />
      <el-card v-for="g in groups" :key="g.name" style="margin-bottom:8px">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span><b>{{ g.name }}</b>：已选 {{ g.passed }}/{{ g.required }} 门</span>
          <el-progress :percentage="g.required ? Math.round(g.passed/g.required*100) : 0" :stroke-width="12" style="flex:1;margin:0 16px" />
          <el-tag :type="g.passed >= g.required ? 'success' : 'danger'" size="small">
            {{ g.passed >= g.required ? '达标' : '未达标' }}
          </el-tag>
        </div>
      </el-card>

      <!-- Audit Result -->
      <el-divider />
      <h3 style="margin-bottom:12px">毕业审核详情</h3>
      <el-empty v-if="!audit" description="尚未提交审核" />
      <el-alert v-else :title="audit.detail" :type="audit.is_graduatable ? 'success' : 'error'" :closable="false" show-icon />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getMyPlan, getMyAudit } from '../api/training'

const plan = ref(null)
const courses = ref([])
const audit = ref(null)
const loading = ref(true)
const typeMap = { compulsory: '必修', limited: '限选', elective: '选修' }

const groups = computed(() => {
  const map = {}
  for (const c of courses.value) {
    if (c.course_type !== 'limited' || !c.limited_group) continue
    if (!map[c.limited_group]) map[c.limited_group] = { name: c.limited_group, passed: 0, required: c.min_required || 0 }
    if (c.status === '已通过') map[c.limited_group].passed++
  }
  return Object.values(map)
})

function typeTag(t) {
  return t === 'limited' ? 'warning' : t === 'elective' ? 'success' : ''
}
function statusTag(s) {
  return s === '已通过' ? 'success' : s === '未修' ? 'info' : 'warning'
}

onMounted(async () => {
  try {
    const [planRes, auditRes] = await Promise.all([
      getMyPlan().catch(() => null),
      getMyAudit().catch(() => null)
    ])
    if (planRes) {
      plan.value = planRes.plan
      courses.value = planRes.courses || []
    }
    if (auditRes && auditRes.audit) {
      audit.value = auditRes.audit
    }
  } finally { loading.value = false }
})
</script>

<style scoped>
.page { max-width: 1000px; margin: 20px auto; padding: 0 16px; }
</style>
