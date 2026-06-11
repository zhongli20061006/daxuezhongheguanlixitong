<template>
  <div class="page-container">
    <!-- Time-based Greeting -->
    <div class="greeting-card">
      <el-icon :size="24" class="greeting-icon">
        <Sunny v-if="greetingType === 'morning'" />
        <Coffee v-else-if="greetingType === 'afternoon'" />
        <Moon v-else />
      </el-icon>
      <span class="greeting-text">{{ greetingText }}，{{ auth.name || '用户' }}</span>
    </div>

    <!-- Stats Row Skeleton -->
    <div v-if="pageLoading" class="stat-cards">
      <div v-for="i in 4" :key="i" class="stat-card-skeleton skeleton-loading">
        <div class="skeleton-icon-block"></div>
        <div style="flex:1">
          <div class="skeleton-stat-value"></div>
          <div class="skeleton-stat-label"></div>
        </div>
      </div>
    </div>

    <!-- Top Stats Row -->
    <div v-else class="stat-cards">
      <div class="stat-card">
        <div class="stat-icon stat-icon--blue">
          <el-icon :size="22"><Tickets /></el-icon>
        </div>
        <div>
          <div class="stat-value">{{ enrolledCount }}</div>
          <div class="stat-label">已选课程</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon--green">
          <el-icon :size="22"><Tickets /></el-icon>
        </div>
        <div>
          <div class="stat-value">{{ totalCredits }}</div>
          <div class="stat-label">总学分</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon--orange">
          <el-icon :size="22"><Document /></el-icon>
        </div>
        <div>
          <div class="stat-value">{{ pendingLeaveCount }}</div>
          <div class="stat-label">待审批</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon stat-icon--purple">
          <el-icon :size="22"><Bell /></el-icon>
        </div>
        <div>
          <div class="stat-value">{{ unreadCount }}</div>
          <div class="stat-label">通知</div>
        </div>
      </div>
    </div>

    <!-- Main Content: Schedule + Notifications -->
    <div class="dashboard-grid">
      <!-- Today's Schedule -->
      <div class="dashboard-card card-schedule">
        <div class="card-header card-header--schedule">
          <el-icon :size="18"><Clock /></el-icon>
          <span>今日课表</span>
        </div>
        <!-- Schedule skeleton -->
        <div v-if="scheduleLoading" class="skeleton-card-content">
          <div v-for="i in 3" :key="i" class="skeleton-schedule-row skeleton-loading">
            <div class="skeleton-time"></div>
            <div class="skeleton-schedule-info">
              <div class="skeleton-schedule-name"></div>
              <div class="skeleton-schedule-place"></div>
            </div>
          </div>
        </div>
        <template v-else>
          <template v-if="todayCourses.length">
            <div v-for="course in todayCourses" :key="course.id" class="schedule-item" :style="{ borderLeftColor: '#409EFF' }">
              <div class="schedule-time">{{ periodTimeMap[course.period] || course.period }}</div>
              <div class="schedule-info">
                <div class="schedule-name">{{ course.course_name }}</div>
                <div class="schedule-place">{{ course.classroom_name }}</div>
              </div>
            </div>
          </template>
          <el-empty v-else description="今日无课" :image-size="80" />
        </template>
      </div>

      <!-- Recent Notifications -->
      <div class="dashboard-card card-notification">
        <div class="card-header card-header--notification">
          <el-icon :size="18"><Bell /></el-icon>
          <span>最近通知</span>
        </div>
        <!-- Notification skeleton -->
        <div v-if="notifLoading" class="skeleton-card-content">
          <div v-for="i in 3" :key="i" class="skeleton-notif-row skeleton-loading">
            <div class="skeleton-notif-title"></div>
            <div class="skeleton-notif-content"></div>
            <div class="skeleton-notif-time"></div>
          </div>
        </div>
        <template v-else>
          <template v-if="notifications.length">
            <div v-for="n in notifications" :key="n.id" class="notif-item">
              <div class="notif-title">{{ n.title }}</div>
              <div class="notif-content">{{ n.content }}</div>
              <div class="notif-time">{{ formatTimeAgo(n.created_at) }}</div>
            </div>
          </template>
          <el-empty v-else description="暂无通知" :image-size="80" />
        </template>
        <div class="view-all" @click="$router.push('/notifications')">查看全部 →</div>
      </div>
    </div>

    <!-- Quick Entry Skeleton -->
    <div v-if="pageLoading" class="quick-entries">
      <div v-for="i in 3" :key="i" class="skeleton-entry-card skeleton-loading">
        <div class="skeleton-entry-icon"></div>
        <div class="skeleton-entry-label"></div>
        <div class="skeleton-entry-badge"></div>
      </div>
    </div>

    <!-- Quick Entry Cards -->
    <div v-else class="quick-entries">
      <div class="entry-card entry-card--selection" @click="$router.push('/selection')">
        <div class="entry-border entry-border--blue"></div>
        <el-icon :size="36" color="#409EFF"><Tickets /></el-icon>
        <div class="entry-label">选课中心</div>
        <div class="entry-badge">{{ enrolledCount }}门已选</div>
      </div>
      <div class="entry-card entry-card--leave" @click="$router.push('/leaves')">
        <div class="entry-border entry-border--orange"></div>
        <el-icon :size="36" color="#E6A23C"><Document /></el-icon>
        <div class="entry-label">请假申请</div>
        <div class="entry-badge">{{ pendingLeaveCount }}条待批</div>
      </div>
      <div class="entry-card entry-card--repair" @click="$router.push('/repairs')">
        <div class="entry-border entry-border--green"></div>
        <el-icon :size="36" color="#67C23A"><Tools /></el-icon>
        <div class="entry-label">报修维修</div>
        <div class="entry-badge">提交报修</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { getMySchedule } from '../api/schedule'
import { getNotifications, getUnreadCount } from '../api/notification'
import { getMyCourses } from '../api/selection'
import { getMyLeaves } from '../api/leave'
import { isWeekInRange } from '../utils/weekParser'
import { Clock, Bell, Tickets, Document, Tools, Sunny, Moon, Coffee } from '@element-plus/icons-vue'

const auth = useAuthStore()

// ── Data state ──
const pageLoading = ref(true)
const scheduleCourses = ref([])
const scheduleLoading = ref(true)
const notifications = ref([])
const notifLoading = ref(true)
const enrolledCount = ref(0)
const totalCredits = ref(0)
const pendingLeaveCount = ref(0)
const unreadCount = ref(0)

// ── Greeting ──
const greetingType = computed(() => {
  const h = new Date().getHours()
  if (h >= 6 && h < 12) return 'morning'
  if (h >= 12 && h < 18) return 'afternoon'
  return 'evening'
})
const greetingText = computed(() => {
  const map = { morning: '上午好', afternoon: '下午好', evening: '晚上好' }
  return map[greetingType.value]
})

// ── Today's courses ──
const periodTimeMap = {
  '1-2': '8:00-9:40',
  '3-4': '10:00-11:40',
  '5-6': '14:00-15:40',
  '7-8': '16:00-17:40',
  '9-10': '19:00-20:40'
}

function getCurrentWeekNumber() {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth() + 1 // 1-based
  let firstDay

  if (month >= 2 && month <= 7) {
    // Spring semester (Feb-Jul): first day March 1
    firstDay = new Date(year, 2, 1)
  } else if (month >= 8) {
    // Fall semester (Aug-Dec): first day September 1
    firstDay = new Date(year, 8, 1)
  } else {
    // January: fall semester of previous academic year
    firstDay = new Date(year - 1, 8, 1)
  }

  const diff = now - firstDay
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  if (days < 0) return -1
  const week = Math.ceil((days + 1) / 7)
  if (week > 0 && week <= 20) return week
  return -1
}

const todayCourses = computed(() => {
  const today = new Date().getDay() || 7 // 0(Sun)→7, 1(Mon)→1 ... 6(Sat)→6
  const weekNum = getCurrentWeekNumber()
  return scheduleCourses.value.filter(c => {
    if (c.day_of_week !== today) return false
    if (weekNum > 0) return isWeekInRange(weekNum, c.weeks)
    return true
  })
})

// ── Time ago helper ──
function formatTimeAgo(dateStr) {
  const now = new Date()
  const date = new Date(dateStr)
  const diff = now - date
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 30) return Math.floor(days / 30) + '个月前'
  if (days > 0) return days + '天前'
  if (hours > 0) return hours + '小时前'
  if (minutes > 0) return minutes + '分钟前'
  return '刚刚'
}

// ── Load data ──
async function loadData() {
  const res = await Promise.allSettled([
    getMySchedule(),
    getNotifications(5, 0),
    getMyCourses(),
    getMyLeaves(),
    getUnreadCount()
  ])

  // Schedule
  scheduleLoading.value = false
  if (res[0].status === 'fulfilled') {
    scheduleCourses.value = res[0].value.schedules || []
  }

  // Notifications
  notifLoading.value = false
  if (res[1].status === 'fulfilled') {
    notifications.value = res[1].value.notifications || []
  }

  // Enrolled courses
  if (res[2].status === 'fulfilled') {
    const courses = res[2].value.courses || []
    enrolledCount.value = courses.length
    totalCredits.value = courses.reduce((sum, c) => sum + (c.credit || 0), 0)
  }

  // Leaves
  if (res[3].status === 'fulfilled') {
    const leaves = res[3].value.leaves || []
    pendingLeaveCount.value = leaves.filter(l =>
      l.status && l.status.includes('审批')
    ).length
  }

  // Unread count
  if (res[4].status === 'fulfilled') {
    const v = res[4].value
    unreadCount.value = typeof v === 'number' ? v : (v?.count ?? 0)
  }

  pageLoading.value = false
}

onMounted(loadData)
</script>

<style scoped>
/* ── Greeting ── */
.greeting-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: linear-gradient(135deg, #1E3A5F 0%, #2D5A87 100%);
  border-radius: 12px;
  padding: 20px 28px;
  margin-bottom: 24px;
  color: #fff;
  box-shadow: 0 2px 8px rgba(30, 58, 95, 0.15);
}
.greeting-icon {
  flex-shrink: 0;
  opacity: 0.9;
}
.greeting-text {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

/* ── Stats Row (overrides global.css .stat-cards) ── */
.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  display: flex;
  align-items: center;
  gap: 14px;
  transition: box-shadow 0.2s, transform 0.2s;
}
.stat-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  transform: translateY(-1px);
}
.stat-icon {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-icon--blue { background: #EFF6FF; color: #409EFF; }
.stat-icon--green { background: #ECFDF5; color: #67C23A; }
.stat-icon--orange { background: #FFFBEB; color: #E6A23C; }
.stat-icon--purple { background: #F5F3FF; color: #8B5CF6; }
.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #1F2937;
  line-height: 1.2;
}
.stat-label {
  font-size: 13px;
  color: #6B7280;
  margin-top: 2px;
}

/* ── Dashboard Two-Column Grid ── */
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}
.dashboard-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1F2937;
  padding-bottom: 14px;
  margin-bottom: 12px;
  border-bottom: 1px solid #F3F4F6;
}
.card-schedule { border-left: 3px solid #409EFF; }
.card-notification { border-left: 3px solid #E6A23C; }

/* ── Schedule Items ── */
.schedule-item {
  display: flex;
  gap: 14px;
  padding: 12px 0 12px 12px;
  margin-bottom: 8px;
  border-left: 3px solid #409EFF;
  border-radius: 0 6px 6px 0;
  background: #F9FAFB;
  transition: background 0.15s;
}
.schedule-item:last-child { margin-bottom: 0; }
.schedule-item:hover { background: #EFF6FF; }
.schedule-time {
  font-size: 13px;
  font-weight: 600;
  color: #409EFF;
  white-space: nowrap;
  min-width: 80px;
  padding-top: 1px;
}
.schedule-info { flex: 1; min-width: 0; }
.schedule-name {
  font-size: 14px;
  font-weight: 600;
  color: #1F2937;
}
.schedule-place {
  font-size: 12px;
  color: #6B7280;
  margin-top: 2px;
}

/* ── Notification Items ── */
.notif-item {
  padding: 10px 0;
  border-bottom: 1px solid #F3F4F6;
  cursor: pointer;
  transition: background 0.15s;
}
.notif-item:last-of-type { border-bottom: none; }
.notif-item:hover { background: #FFFBEB; margin: 0 -12px; padding-left: 12px; padding-right: 12px; border-radius: 6px; }
.notif-title {
  font-size: 14px;
  font-weight: 600;
  color: #1F2937;
  margin-bottom: 3px;
}
.notif-content {
  font-size: 12px;
  color: #6B7280;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
.notif-time {
  font-size: 11px;
  color: #9CA3AF;
  margin-top: 5px;
}
.view-all {
  text-align: right;
  font-size: 13px;
  color: #409EFF;
  cursor: pointer;
  padding-top: 12px;
  border-top: 1px solid #F3F4F6;
  margin-top: auto;
  transition: color 0.15s;
}
.view-all:hover { color: #2563EB; }

/* ── Quick Entry Cards ── */
.quick-entries {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}
.entry-card {
  position: relative;
  background: #fff;
  border-radius: 12px;
  padding: 28px 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.25s, box-shadow 0.25s;
}
.entry-card:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 8px 25px rgba(0,0,0,0.1);
}
.entry-border {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
}
.entry-border--blue { background: #409EFF; }
.entry-border--orange { background: #E6A23C; }
.entry-border--green { background: #67C23A; }
.entry-label {
  font-size: 16px;
  font-weight: 600;
  color: #1F2937;
}
.entry-badge {
  font-size: 13px;
  color: #6B7280;
  background: #F3F4F6;
  padding: 3px 14px;
  border-radius: 12px;
}

/* ── Responsive ── */
@media (max-width: 900px) {
  .stat-cards { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .dashboard-grid { grid-template-columns: 1fr; }
  .quick-entries { grid-template-columns: 1fr; }
  .greeting-card { padding: 16px 20px; }
  .greeting-text { font-size: 17px; }
}
@media (max-width: 480px) {
  .stat-cards { grid-template-columns: 1fr 1fr; gap: 10px; }
  .stat-card { padding: 12px 14px; }
  .stat-value { font-size: 20px; }
}

/* ── Skeleton Animation ── */
@keyframes skeleton-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
.skeleton-loading {
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}

/* ── Stats row skeleton ── */
.stat-card-skeleton {
  background: #fff;
  border-radius: 8px;
  padding: 16px 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  display: flex;
  align-items: center;
  gap: 14px;
}
.skeleton-icon-block {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  background: #e5e7eb;
  flex-shrink: 0;
}
.skeleton-stat-value {
  height: 24px;
  width: 60px;
  background: #e5e7eb;
  border-radius: 4px;
  margin-bottom: 6px;
}
.skeleton-stat-label {
  height: 14px;
  width: 80px;
  background: #e5e7eb;
  border-radius: 4px;
}

/* ── Schedule skeleton ── */
.skeleton-card-content {
  padding: 4px 0;
}
.skeleton-schedule-row {
  display: flex;
  gap: 14px;
  padding: 12px 0 12px 12px;
  margin-bottom: 8px;
  border-left: 3px solid #e5e7eb;
  border-radius: 0 6px 6px 0;
  background: #f9fafb;
}
.skeleton-time {
  width: 80px;
  height: 16px;
  background: #e5e7eb;
  border-radius: 4px;
  flex-shrink: 0;
}
.skeleton-schedule-info {
  flex: 1;
}
.skeleton-schedule-name {
  height: 16px;
  width: 120px;
  background: #e5e7eb;
  border-radius: 4px;
  margin-bottom: 6px;
}
.skeleton-schedule-place {
  height: 13px;
  width: 90px;
  background: #e5e7eb;
  border-radius: 4px;
}

/* ── Notification skeleton ── */
.skeleton-notif-row {
  padding: 12px 0;
  border-bottom: 1px solid #f3f4f6;
}
.skeleton-notif-title {
  height: 15px;
  width: 180px;
  background: #e5e7eb;
  border-radius: 4px;
  margin-bottom: 6px;
}
.skeleton-notif-content {
  height: 13px;
  width: 260px;
  background: #e5e7eb;
  border-radius: 4px;
  margin-bottom: 6px;
}
.skeleton-notif-time {
  height: 11px;
  width: 60px;
  background: #e5e7eb;
  border-radius: 4px;
}

/* ── Quick entry skeleton ── */
.skeleton-entry-card {
  background: #fff;
  border-radius: 12px;
  padding: 28px 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
}
.skeleton-entry-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: #e5e7eb;
}
.skeleton-entry-label {
  height: 16px;
  width: 80px;
  background: #e5e7eb;
  border-radius: 4px;
}
.skeleton-entry-badge {
  height: 22px;
  width: 60px;
  background: #e5e7eb;
  border-radius: 12px;
}
</style>
