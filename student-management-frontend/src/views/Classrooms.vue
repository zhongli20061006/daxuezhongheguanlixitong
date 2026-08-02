<template>
  <div class="page-container">
    <h2 class="page-title">空闲教室</h2>
    <div class="content-card">
      <el-form :inline="true" :model="query" label-width="auto">
        <el-form-item label="*教学周"><el-input-number v-model="query.week" :min="1" :max="18" /></el-form-item>
        <el-form-item label="*星期"><el-select v-model="query.day_of_week" style="width:120px"><el-option v-for="(n,i) in weekdays" :key="i+1" :label="n" :value="i+1" /></el-select></el-form-item>
        <el-form-item label="*节次"><el-select v-model="query.period" style="width:130px"><el-option v-for="p in periods" :key="p" :label="p" :value="p" /></el-select></el-form-item>
        <el-form-item label="最低人数"><el-input-number v-model="query.min_capacity" :min="0" /></el-form-item>
        <el-form-item><el-button type="primary" @click="search" :loading="loading" style="width:120px">查询</el-button><el-button @click="reset">重置</el-button></el-form-item>
      </el-form>
    </div>
    <div v-if="rooms.length" class="room-grid">
      <div v-for="r in rooms" :key="r.id" class="room-card" @click="showDetail(r)">
        <div class="room-top"><span class="room-name">{{ r.name }}</span><el-tag size="small" type="success">空闲</el-tag></div>
        <div class="room-info">👥 {{ r.capacity }}人</div>
        <div class="room-info">🏢 {{ r.building || '-' }}</div>
        <div class="room-tags">
          <el-tag v-if="r.has_projector" size="small" type="primary">投影</el-tag>
          <el-button size="small" type="primary" @click.stop="showReserve(r)" :disabled="!canReserve">预约</el-button>
        </div>
      </div>
    </div>
    <el-empty v-else-if="queried" description="该时段暂无空闲教室" :image-size="80" />
    <div class="content-card" style="margin-top:24px">
      <h3 style="margin-bottom:12px">我的预约</h3>
      <div v-if="myReservations.length" class="room-grid" style="grid-template-columns:repeat(auto-fill,minmax(260px,1fr))">
        <div v-for="r in myReservations" :key="r.id" :class="['room-card', r.status]">
          <div class="room-top"><span class="room-name">{{ r.classroom_name }}</span><el-tag :type="r.status==='已预约'?'success':'info'" size="small">{{ r.status }}</el-tag></div>
          <div class="room-info">📅 第{{ r.week }}周 周{{ r.day_of_week }} {{ r.period }}节</div>
          <div class="room-info">📝 {{ r.reason }}</div>
          <div style="margin-top:8px"><el-button v-if="r.status==='已预约'" size="small" type="danger" @click.stop="doCancel(r.id)">取消</el-button></div>
        </div>
      </div>
      <el-empty v-else description="暂无预约记录" :image-size="80" />
    </div>
    <el-dialog v-model="detailVisible" title="教室占用详情" width="420px">
      <div v-if="detailData && !detailData.available"><p><b>占用课程：</b>{{ detailData.occupied_by?.course_name }}</p><p><b>教师：</b>{{ detailData.occupied_by?.teacher_name }}</p><p><b>周次：</b>{{ detailData.occupied_by?.weeks }}</p><p><b>时间：</b>周{{ detailData.occupied_by?.day_of_week }} {{ detailData.occupied_by?.period }}节</p></div>
      <el-empty v-else description="该时段无课程占用" :image-size="80" />
    </el-dialog>
    <el-dialog v-model="reserveVisible" title="预约教室" width="400px">
      <el-descriptions :column="1" border style="margin-bottom:12px"><el-descriptions-item label="教室">{{ reserveForm.classroom_name }}</el-descriptions-item><el-descriptions-item label="时间">第{{ query.week }}周 周{{ query.day_of_week }} {{ query.period }}节</el-descriptions-item></el-descriptions>
      <el-input v-model="reserveForm.reason" type="textarea" :rows="2" placeholder="例如：自习、小组讨论" maxlength="200" show-word-limit />
      <template #footer><el-button @click="reserveVisible=false">取消</el-button><el-button type="primary" @click="doReserve" :loading="reserving">确认预约</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAvailableClassrooms, getClassroomAvailability, reserveClassroom, getMyReservations, cancelReservation } from '../api/classroom'

const weekdays = ['周一','周二','周三','周四','周五','周六','周日']
const periods = ['1-2','3-4','5-6','7-8','9-10']
const query = ref({ week:null, day_of_week:null, period:'', min_capacity:0 })
const rooms = ref([]); const loading = ref(false); const queried = ref(false)
const detailVisible = ref(false); const detailData = ref(null)
const reserveVisible = ref(false); const reserveForm = ref({ classroom_id:null, classroom_name:'', reason:'' }); const reserving = ref(false)
const myReservations = ref([])
const canReserve = computed(() => query.value.week && query.value.day_of_week && query.value.period)

async function search() { loading.value=true; queried.value=true; try { const r=await getAvailableClassrooms(query.value); rooms.value=r.classrooms||[] } finally { loading.value=false } }
function reset() { query.value={ week:null, day_of_week:null, period:'', min_capacity:0 }; rooms.value=[]; queried.value=false }
async function showDetail(row) { try { detailData.value=await getClassroomAvailability(row.id,{ week:query.value.week, day_of_week:query.value.day_of_week, period:query.value.period }); detailVisible.value=true } catch {} }
function showReserve(row) { reserveForm.value={ classroom_id:row.id, classroom_name:row.name, reason:'' }; reserveVisible.value=true }
async function doReserve() { if(!reserveForm.value.reason){ElMessage.warning('请填写预约理由');return} reserving.value=true; try { await reserveClassroom({ classroom_id:reserveForm.value.classroom_id, week:query.value.week, day_of_week:query.value.day_of_week, period:query.value.period, reason:reserveForm.value.reason }); ElMessage.success('预约成功'); reserveVisible.value=false; search(); loadMyReservations() } catch(e) { ElMessage.error(e?.response?.data?.detail||'预约失败') } finally { reserving.value=false } }
async function loadMyReservations() { try { const r=await getMyReservations(); myReservations.value=r.reservations||[] } catch {} }
async function doCancel(id) { try { await ElMessageBox.confirm('确定取消该预约？','确认'); await cancelReservation(id); ElMessage.success('已取消'); loadMyReservations(); search() } catch {} }
onMounted(loadMyReservations)
</script>

<style scoped>
/* ── Page Header Enhancement ── */
.page-title {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: var(--space-lg);
  padding-bottom: var(--space-md);
  border-bottom: 2px solid var(--color-border-light);
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.3px;
}
.page-title::before {
  content: '';
  width: 4px;
  height: 24px;
  background: var(--color-success);
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

/* ── Search Card Enhancement ── */
.content-card:first-of-type {
  border-top: 3px solid var(--color-success);
  animation: fadeInUp 0.35s ease-out;
}

/* ── Room Grid ── */
.room-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-md);
  margin-bottom: var(--space-lg);
  animation: fadeInUp 0.4s ease-out;
}

/* ── Room Card ── */
.room-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  box-shadow: var(--shadow-sm);
  border-left: 4px solid var(--color-success);
  cursor: pointer;
  transition: transform var(--transition-base), box-shadow var(--transition-base);
  border: 1px solid var(--color-border-light);
}
.room-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}
.room-card.已取消 {
  border-left-color: var(--color-text-muted);
  opacity: 0.7;
}

/* ── Room Card Inner Elements ── */
.room-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.room-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.room-info {
  font-size: 13px;
  color: var(--color-text-tertiary);
  margin: 3px 0;
}
.room-tags {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 6px;
}

/* ── "My Reservations" Card ── */
.content-card + .content-card {
  border-top: 3px solid var(--color-info);
}

/* ── "My Reservations" Heading ── */
h3 {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: var(--space-md);
  letter-spacing: -0.2px;
}

/* ── Empty State Enhancement ── */
.el-empty__description {
  color: var(--color-text-muted);
  font-size: 14px;
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .page-title { font-size: 19px; }
  .room-grid { grid-template-columns: 1fr; gap: 10px; }
  .room-card { padding: 14px; }
}
</style>
