<template>
  <div style="padding:20px">
    <h2 style="margin-bottom:16px">空闲教室查询</h2>
    <el-form :inline="true" :model="query">
      <el-form-item label="教学周">
        <el-input-number v-model="query.week" :min="1" :max="18" />
      </el-form-item>
      <el-form-item label="星期">
        <el-select v-model="query.day_of_week" style="width:120px">
          <el-option v-for="(n,i) in weekdays" :key="i+1" :label="n" :value="i+1" />
        </el-select>
      </el-form-item>
      <el-form-item label="节次">
        <el-select v-model="query.period" style="width:140px">
          <el-option v-for="p in periods" :key="p" :label="p" :value="p" />
        </el-select>
      </el-form-item>
      <el-form-item label="最低人数">
        <el-input-number v-model="query.min_capacity" :min="0" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="search" :loading="loading">查询</el-button>
        <el-button @click="reset">重置</el-button>
      </el-form-item>
    </el-form>
    <el-table :data="rooms" v-loading="loading" stripe empty-text="请选择条件后查询">
      <el-table-column prop="name" label="教室" />
      <el-table-column prop="building" label="教学楼" />
      <el-table-column prop="capacity" label="容纳人数" />
      <el-table-column label="多媒体">
        <template #default="{row}">
          <el-tag :type="row.has_projector ? 'success' : 'info'">{{ row.has_projector ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{row}">
          <el-button size="small" @click="showDetail(row)">查看详情</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="dialogVisible" title="教室占用详情" width="400px">
      <div v-if="detailData && !detailData.available">
        <p><b>占用课程：</b>{{ detailData.occupied_by?.course_name }}</p>
        <p><b>教师：</b>{{ detailData.occupied_by?.teacher_name }}</p>
        <p><b>周次：</b>{{ detailData.occupied_by?.weeks }}</p>
        <p><b>时间：</b>周{{ detailData.occupied_by?.day_of_week }} {{ detailData.occupied_by?.period }}节</p>
      </div>
      <el-empty v-else description="该时段无课程占用" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { getAvailableClassrooms, getClassroomAvailability } from '../api/classroom'

const weekdays = ['周一','周二','周三','周四','周五','周六','周日']
const periods = ['1-2','3-4','5-6','7-8','9-10']
const query = ref({ week: null, day_of_week: null, period: '', min_capacity: 0 })
const rooms = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const detailData = ref(null)

async function search() {
  loading.value = true
  try {
    const res = await getAvailableClassrooms(query.value)
    rooms.value = res.classrooms || []
  } finally { loading.value = false }
}

function reset() { query.value = { week: null, day_of_week: null, period: '', min_capacity: 0 }; rooms.value = [] }

async function showDetail(row) {
  try {
    detailData.value = await getClassroomAvailability(row.id, { week: query.value.week, day_of_week: query.value.day_of_week, period: query.value.period })
    dialogVisible.value = true
  } catch {}
}
</script>
