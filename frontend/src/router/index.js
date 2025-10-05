import { createRouter, createWebHistory } from 'vue-router'
import AdminManagerLogin from '../views/AdminManagerLogin.vue'
import Home from '../views/Home.vue'
import AdminDashboard from '../views/AdminDashboard.vue'
import TeacherBulkGenerate from '../views/TeacherBulkGenerate.vue'
import AdminCompetitionManage from '../views/AdminCompetitionManage.vue'
import AdminAuditLogs from '../views/AdminAuditLogs.vue'
import AdminAnnouncements from '../views/AdminAnnouncements.vue'
import TeamEnroll from '../views/TeamEnroll.vue'
import StudentRegister from '../views/StudentRegister.vue'
import TeacherLogin from '../views/TeacherLogin.vue'
import TeacherDashboard from '../views/TeacherDashboard.vue'
import TeacherSubmissions from '../views/TeacherSubmissions.vue'
import TeacherSubmissionDetail from '../views/TeacherSubmissionDetail.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: Home },
    { path: '/admin-manager', name: 'admin-manager', component: AdminManagerLogin },
    { path: '/admin-dashboard', name: 'admin-dashboard', component: AdminDashboard },
    { path: '/admin/teachers/generate', name: 'admin-teachers-generate', component: TeacherBulkGenerate },
    { path: '/admin/competitions/manage', name: 'admin-competitions-manage', component: AdminCompetitionManage },
    { path: '/admin/announcements', name: 'admin-announcements', component: AdminAnnouncements },
    { path: '/admin/audit/logs', name: 'admin-audit-logs', component: AdminAuditLogs },
    { path: '/team/enroll', name: 'team-enroll', component: TeamEnroll },
    { path: '/student/register', name: 'student-register', component: StudentRegister },
    { path: '/teacher-login', name: 'teacher-login', component: TeacherLogin },
    { path: '/teacher', name: 'teacher-dashboard', component: TeacherDashboard },
    { path: '/teacher/competitions/:seasonId/submissions', name: 'teacher-submissions', component: TeacherSubmissions },
    { path: '/teacher/submissions/:submissionId', name: 'teacher-submission-detail', component: TeacherSubmissionDetail },
  ],
})

// 简单的管理员访问守卫：要求本地存储有 auth 且 role=admin
router.beforeEach((to, from, next) => {
  const protectedRoutes = ['admin-dashboard', 'admin-teachers-generate', 'admin-competitions-manage', 'admin-announcements']
  const teacherRoutes = ['teacher-dashboard', 'teacher-submissions', 'teacher-submission-detail']
  if (protectedRoutes.includes(to.name)) {
    try {
      const raw = localStorage.getItem('auth')
      const auth = raw ? JSON.parse(raw) : null
      if (auth?.role === 'admin' && auth?.token) {
        return next()
      }
    } catch {}
    // 没有权限，跳回登录页
    return next({ name: 'admin-manager', query: { redirect: to.fullPath } })
  }
  if (teacherRoutes.includes(to.name)) {
    try {
      const raw = localStorage.getItem('auth')
      const auth = raw ? JSON.parse(raw) : null
      if (auth?.role === 'teacher' && auth?.token) {
        return next()
      }
    } catch {}
    return next({ name: 'teacher-login', query: { redirect: to.fullPath } })
  }
  next()
})

export default router