<template>
  <div class="time-range-picker">
    <el-select v-model="week" placeholder="教学周" style="width:120px">
      <el-option v-for="w in 18" :key="w" :label="`第${w}周`" :value="w" />
    </el-select>
    <el-select v-model="day" placeholder="星期" style="width:110px">
      <el-option v-for="(d,i) in dayLabels" :key="i+1" :label="d" :value="i+1" />
    </el-select>
    <el-select v-model="period" placeholder="节次" style="width:120px">
      <el-option v-for="p in periodOptions" :key="p.value" :label="p.label" :value="p.value" />
    </el-select>
    <slot />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const week = ref(1), day = ref(1), period = ref('1-2')
const dayLabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const periodOptions = [
  { label: '第1-2节', value: '1-2' }, { label: '第3-4节', value: '3-4' },
  { label: '第5-6节', value: '5-6' }, { label: '第7-8节', value: '7-8' },
  { label: '第9-10节', value: '9-10' },
]

const emit = defineEmits(['change'])
watch([week, day, period], () => emit('change', { week: week.value, day: day.value, period: period.value }), { immediate: true })
</script>

<style scoped>
.time-range-picker { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
</style>
