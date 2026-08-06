<template>
  <div class="page-container">
    <!-- Time-based Greeting -->
    <div class="greeting-block">
      <h1 class="greeting-title">{{ greetingText }}，{{ auth.name || '用户' }}</h1>
      <p class="greeting-date">{{ todayText }}</p>
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
            <div v-for="course in todayCourses" :key="course.id" class="schedule-item">
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
    <div v-if="pageLoading" class="quick-links">
      <div v-for="i in 3" :key="i" class="skeleton-entry-card skeleton-loading">
        <div class="skeleton-entry-icon"></div>
        <div class="skeleton-entry-label"></div>
        <div class="skeleton-entry-badge"></div>
      </div>
    </div>

    <!-- Quick Entry Links -->
    <div v-else class="quick-links">
      <div class="quick-link" @click="$router.push('/selection')">
        <el-icon :size="18"><Tickets /></el-icon>
        <span class="quick-label">选课中心</span>
        <span class="quick-meta">{{ enrolledCount }}门已选</span>
      </div>
      <div class="quick-link" @click="$router.push('/leaves')">
        <el-icon :size="18"><Document /></el-icon>
        <span class="quick-label">请假申请</span>
        <span class="quick-meta">{{ pendingLeaveCount }}条待批</span>
      </div>
      <div class="quick-link" @click="$router.push('/repairs')">
        <el-icon :size="18"><Tools /></el-icon>
        <span class="quick-label">报修维修</span>
        <span class="quick-meta">提交报修</span>
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
import { Clock, Bell, Tickets, Document, Tools } from '@element-plus/icons-vue'

const auth = useAuthStore()

// ── Today's date ──
const todayText = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })

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
.greeting-block {
  margin-bottom: 24px;
}
.greeting-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.5px;
  margin: 0;
}
.greeting-date {
  font-size: 13px;
  color: var(--color-text-tertiary);
  margin: 6px 0 0;
}

/* ── Stats Row ── */
.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.stat-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: 18px 22px;
  box-shadow: var(--shadow-xs);
  display: flex;
  align-items: center;
  gap: 16px;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  border: 1px solid var(--color-border-light);
}
.stat-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-icon--blue { background: var(--gradient-tech); color: #fff; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25); }
.stat-icon--green { background: var(--color-success-bg); color: var(--color-success); }
.stat-icon--orange { background: var(--color-warning-bg); color: var(--color-warning); }
.stat-icon--purple { background: var(--color-info-bg); color: var(--color-info); }
.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.2;
  letter-spacing: -0.5px;
  font-variant-numeric: tabular-nums;
}
.stat-label {
  font-size: 13px;
  color: var(--color-text-tertiary);
  margin-top: 3px;
}

/* ── Dashboard Two-Column Grid (asymmetric) ── */
.dashboard-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}
.dashboard-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: 22px;
  box-shadow: var(--shadow-xs);
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-border-light);
  transition: box-shadow 0.25s ease;
}
.dashboard-card:hover {
  box-shadow: var(--shadow-sm);
}
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text-primary);
  padding-bottom: 14px;
  margin-bottom: 14px;
  border-bottom: 1px solid var(--color-border-light);
}

/* ── Schedule Items ── */
.schedule-item {
  display: flex;
  gap: 14px;
  padding: 14px 0 14px 14px;
  margin-bottom: 10px;
  border-left: 3px solid var(--color-primary);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  background: var(--color-bg-alt);
  transition: background 0.2s ease, transform 0.2s ease;
}
.schedule-item:last-child { margin-bottom: 0; }
.schedule-item:hover {
  background: var(--color-primary-bg);
  transform: translateX(4px);
}
.schedule-time {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
  white-space: nowrap;
  min-width: 80px;
  padding-top: 1px;
  font-variant-numeric: tabular-nums;
}
.schedule-info { flex: 1; min-width: 0; }
.schedule-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.schedule-place {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-top: 2px;
}

/* ── Notification Items ── */
.notif-item {
  padding: 10px 0;
  border-bottom: 1px solid var(--color-border-light);
  cursor: pointer;
  transition: background 0.15s;
}
.notif-item:last-of-type { border-bottom: none; }
.notif-item:hover {
  background: var(--color-bg-alt);
  margin: 0 -12px;
  padding-left: 12px;
  padding-right: 12px;
  border-radius: var(--radius-sm);
}
.notif-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 3px;
}
.notif-content {
  font-size: 12px;
  color: var(--color-text-secondary);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
.notif-time {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 5px;
}
.view-all {
  text-align: right;
  font-size: 13px;
  color: var(--color-primary);
  cursor: pointer;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
  margin-top: auto;
  transition: color 0.15s;
}
.view-all:hover { color: var(--color-tech); }

/* ── Quick Entry Links ── */
.quick-links {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.quick-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: border-color var(--transition-fast), color var(--transition-fast), background var(--transition-fast);
}
.quick-link:hover {
  border-color: var(--color-tech);
  color: var(--color-tech);
  background: var(--color-tech-bg);
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.12);
}
.quick-label {
  font-size: 14px;
  font-weight: 600;
}
.quick-meta {
  margin-left: auto;
  font-size: 12px;
  color: var(--color-text-muted);
}

/* ── Responsive ── */
@media (max-width: 900px) {
  .stat-cards { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .dashboard-grid { grid-template-columns: 1fr; }
  .quick-links { grid-template-columns: 1fr; }
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
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  box-shadow: var(--shadow-xs);
  display: flex;
  align-items: center;
  gap: 14px;
}
.skeleton-icon-block {
  width: 42px;
  height: 42px;
  border-radius: var(--radius-md);
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
  background: var(--color-bg-alt);
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
  border-bottom: 1px solid var(--color-border-light);
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
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: 28px 20px;
  box-shadow: var(--shadow-xs);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
}
.skeleton-entry-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
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
  border-radius: var(--radius-full);
}
</style>
