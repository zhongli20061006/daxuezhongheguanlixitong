import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { roles: [] } },
  { path: '/change-password', name: 'ChangePassword', component: () => import('../views/ChangePassword.vue'), meta: { roles: ['student', 'teacher', 'staff', 'admin'] } },
  { path: '/schedule', name: 'Schedule', component: () => import('../views/Schedule.vue'), meta: { roles: ['student'] } },
  { path: '/selection', name: 'Selection', component: () => import('../views/Selection.vue'), meta: { roles: ['student'] } },
  { path: '/classrooms', name: 'Classrooms', component: () => import('../views/Classrooms.vue'), meta: { roles: ['student', 'teacher', 'staff', 'admin'] } },
  { path: '/scores', name: 'Scores', component: () => import('../views/Scores.vue'), meta: { roles: ['student'] } },
  { path: '/scores/input', name: 'ScoreInput', component: () => import('../views/ScoreInput.vue'), meta: { roles: ['teacher'] } },
  { path: '/repairs', name: 'Repairs', component: () => import('../views/Repairs.vue'), meta: { roles: ['student', 'teacher', 'staff', 'admin'] } },
  { path: '/repairs/manage', name: 'RepairManage', component: () => import('../views/RepairManage.vue'), meta: { roles: ['staff', 'admin'] } },
  { path: '/admin', name: 'Admin', component: () => import('../views/Admin.vue'), meta: { roles: ['admin'] } },
  { path: '/leaves', name: 'Leaves', component: () => import('../views/Leaves.vue'), meta: { roles: ['student'] } },
  { path: '/plan', name: 'MyPlan', component: () => import('../views/MyPlan.vue'), meta: { roles: ['student'] } },
  { path: '/my-exams', name: 'MyExams', component: () => import('../views/MyExams.vue'), meta: { roles: ['student'] } },
  { path: '/my-invigilations', name: 'MyInvigilations', component: () => import('../views/MyInvigilations.vue'), meta: { roles: ['teacher'] } },
  { path: '/advisor', name: 'AdvisorApproval', component: () => import('../views/AdvisorApproval.vue'), meta: { roles: ['teacher', 'admin'] } },
  { path: '/notifications', name: 'Notifications', component: () => import('../views/Notifications.vue'), meta: { roles: ['student', 'teacher', 'staff', 'admin'] } },
  { path: '/profile', name: 'Profile', component: () => import('../views/Profile.vue'), meta: { roles: ['student', 'teacher', 'staff', 'admin'] } },
  { path: '/', redirect: '/login' },
  { path: '/:pathMatch(.*)*', redirect: '/login' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const defaultPages = { student: '/schedule', teacher: '/scores/input', staff: '/repairs/manage', admin: '/admin' }

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('sms_token')
  const mustChange = localStorage.getItem('sms_must_change') === 'true'
  const role = localStorage.getItem('sms_role')

  if (!token && to.path !== '/login') return next('/login')
  if (token && mustChange && to.path !== '/change-password') return next('/change-password')
  if (to.meta.roles && to.meta.roles.length > 0 && !to.meta.roles.includes(role)) {
    return next(defaultPages[role] || '/login')
  }
  next()
})

export default router
