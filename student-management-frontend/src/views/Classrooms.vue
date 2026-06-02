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
      <el-table-column label="操作" width="180">
        <template #default="{row}">
          <el-button size="small" @click="showDetail(row)">查看</el-button>
          <el-button size="small" type="primary" @click="showReserve(row)" :disabled="!canReserve">预约</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 预约弹窗 -->
    <el-dialog v-model="reserveVisible" title="预约教室" width="400px">
      <el-descriptions :column="1" border style="margin-bottom:12px">
        <el-descriptions-item label="教室">{{ reserveForm.classroom_name }}</el-descriptions-item>
        <el-descriptions-item label="时间">第{{ query.week }}周 周{{ query.day_of_week }} {{ query.period }}节</el-descriptions-item>
      </el-descriptions>
      <el-form>
        <el-form-item label="预约理由">
          <el-input v-model="reserveForm.reason" type="textarea" :rows="2" placeholder="例如：自习、小组讨论" maxlength="200" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reserveVisible=false">取消</el-button>
        <el-button type="primary" @click="doReserve" :loading="reserving">确认预约</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="教室占用详情" width="400px">
      <div v-if="detailData && !detailData.available">
        <p><b>占用课程：</b>{{ detailData.occupied_by?.course_name }}</p>
        <p><b>教师：</b>{{ detailData.occupied_by?.teacher_name }}</p>
        <p><b>周次：</b>{{ detailData.occupied_by?.weeks }}</p>
        <p><b>时间：</b>周{{ detailData.occupied_by?.day_of_week }} {{ detailData.occupied_by?.period }}节</p>
      </div>
      <el-empty v-else description="该时段无课程占用" />
    </el-dialog>

    <!-- 我的预约 -->
    <el-divider />
    <h3 style="margin-bottom:12px">我的预约</h3>
    <el-table :data="myReservations" stripe empty-text="暂无预约记录">
      <el-table-column prop="classroom_name" label="教室" />
      <el-table-column label="时间">
        <template #default="{row}"> 第{{ row.week }}周 周{{ row.day_of_week }} {{ row.period }}节 </template>
      </el-table-column>
      <el-table-column prop="reason" label="理由" min-width="150" show-overflow-tooltip />
      <el-table-column label="状态" width="80">
        <template #default="{row}">
          <el-tag :type="row.status === '已预约' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="时间" width="140" />
      <el-table-column label="操作" width="80">
        <template #default="{row}">
          <el-button v-if="row.status === '已预约'" size="small" type="danger" @click="doCancel(row.id)">取消</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAvailableClassrooms, getClassroomAvailability, reserveClassroom, getMyReservations, cancelReservation } from '../api/classroom'

const weekdays = ['周一','周二','周三','周四','周五','周六','周日']
const periods = ['1-2','3-4','5-6','7-8','9-10']
const query = ref({ week: null, day_of_week: null, period: '', min_capacity: 0 })
const rooms = ref([])
const loading = ref(false)
const detailVisible = ref(false)
const detailData = ref(null)
const reserveVisible = ref(false)
const reserveForm = ref({ classroom_id: null, classroom_name: '', reason: '' })
const reserving = ref(false)
const myReservations = ref([])

const canReserve = computed(() => query.value.week && query.value.day_of_week && query.value.period)

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
    detailVisible.value = true
  } catch {}
}

function showReserve(row) {
  reserveForm.value = { classroom_id: row.id, classroom_name: row.name, reason: '' }
  reserveVisible.value = true
}

async function doReserve() {
  if (!reserveForm.value.reason) { ElMessage.warning('请填写预约理由'); return }
  reserving.value = true
  try {
    await reserveClassroom({
      classroom_id: reserveForm.value.classroom_id,
      week: query.value.week,
      day_of_week: query.value.day_of_week,
      period: query.value.period,
      reason: reserveForm.value.reason,
    })
    ElMessage.success('预约成功')
    reserveVisible.value = false
    search()
    loadMyReservations()
  } catch (e) { ElMessage.error(e?.response?.data?.detail || '预约失败') }
  finally { reserving.value = false }
}

async function loadMyReservations() {
  try {
    const res = await getMyReservations()
    myReservations.value = res.reservations || []
  } catch {}
}

async function doCancel(id) {
  try {
    await ElMessageBox.confirm('确定取消该预约？', '确认')
    await cancelReservation(id)
    ElMessage.success('已取消')
    loadMyReservations()
    search()
  } catch {}
}

onMounted(loadMyReservations)
</script>
