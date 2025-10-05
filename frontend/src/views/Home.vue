<template>
  <div class="home">
    <header class="home-header glass-header">
      <div class="brand">数学建模校赛</div>
      <nav class="nav-links">
        <a href="#">首页</a>
        <a href="#">研究领域</a>
        <a href="#">成果展示</a>
        <a href="#">关于我们</a>
      </nav>
      <div class="actions">
        <el-button v-if="!studentAuthed" class="ghost" type="primary" @click="showLogin = true">学生登录</el-button>
        <el-dropdown v-else>
          <span class="el-dropdown-link">
            学生：{{ studentProfileText }}<el-icon class="el-icon--right"><i-ep-arrow-down /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <main class="home-content layout">
      <section class="section main-left">
        <h2>历年优秀作品</h2>
        <el-skeleton v-if="loading.works" :rows="4" animated />
        <div v-else class="works-grid">
          <el-card v-for="w in excellentWorks" :key="w.id" class="work-card glass-card" shadow="hover">
            <div class="work-meta">
              <div class="work-title">赛季 #{{ w.season_id }}</div>
              <div class="work-summary">{{ w.summary || '（暂无摘要）' }}</div>
              <div class="work-extra">评分：{{ w.score ?? '未评' }} | 上传：{{ formatTime(w.created_at) }}</div>
            </div>
            <div class="work-files" v-if="w.files && w.files.length">
              <el-tag v-for="f in w.files" :key="f.id" type="success" effect="plain" class="file-tag">
                <a :href="f.downloadUrl || 'javascript:void(0)'" :class="{ disabled: !f.downloadUrl }" target="_blank">{{ f.filename }}</a>
              </el-tag>
            </div>
          </el-card>
        </div>
      </section>

      <section class="section main-left">
        <h2>开放报名的竞赛</h2>
        <el-skeleton v-if="loading.comps" :rows="3" animated />
        <el-empty v-else-if="openCompetitions.length === 0" description="当前无开放报名的竞赛" />
        <el-table v-else :data="openCompetitions" border stripe class="glass-table">
          <el-table-column prop="name" label="竞赛名称" min-width="160" />
          <el-table-column label="报名时间" min-width="220">
            <template #default="{ row }">
              {{ formatTime(row.signup_start) }} ~ {{ formatTime(row.signup_end) }}
            </template>
          </el-table-column>
          <el-table-column label="开赛时间" min-width="180">
            <template #default="{ row }">
              {{ formatTime(row.start_time) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-button class="ghost" type="primary" size="small" @click="goTeamEnroll(row)">报名</el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <aside class="sidebar">
        <div class="announce-card glass-card">
          <div class="header">
            <h3>公告</h3>
            <div class="pager">
              <el-button class="ghost" size="small" @click="prevPage" :disabled="announcePage === 1">上一页</el-button>
              <span class="page-text">{{ announcePage }} / {{ totalPages }}</span>
              <el-button class="ghost" size="small" @click="nextPage" :disabled="announcePage >= totalPages">下一页</el-button>
            </div>
          </div>
          <el-skeleton v-if="loading.ann" :rows="3" animated />
          <div v-else>
            <el-empty v-if="announcements.length === 0" description="暂无公告" />
            <ul v-else class="announce-list">
              <li v-for="a in announcements" :key="a.id" class="announce-item">
                <div class="row">
                  <span class="title">{{ a.title }}</span>
                  <span class="time">{{ formatTime(a.publishedAt) }}</span>
                </div>
                <p class="content">{{ a.content }}</p>
              </li>
            </ul>
          </div>
        </div>
      </aside>
    </main>

    <!-- 学生登录弹窗（桌面优先固定宽度与标签宽度） -->
    <el-dialog v-model="showLogin" title="学生登录" width="560px">
      <el-form :model="loginForm" label-width="120px">
        <el-form-item label="学号">
          <el-input v-model="loginForm.studentId" placeholder="例如：20230001" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="loginForm.email" placeholder="可选，学号或邮箱其一" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showLogin = false">取消</el-button>
        <el-button type="default" @click="goRegister">去注册</el-button>
        <el-button type="primary" :loading="loginLoading" @click="doStudentLogin">登录</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listExcellentWorks, listOpenCompetitions, listAnnouncements } from '../api/public'
import { studentLogin } from '../api/student'
import { useRouter } from 'vue-router'
// 在 <script setup> 中正确获取路由实例
const router = useRouter()

const excellentWorks = ref([])
const openCompetitions = ref([])
const loading = ref({ works: true, comps: true, ann: true })

// 公告分页状态
const announcePage = ref(1)
const pageSize = ref(3)
const announcements = ref([])
const total = ref(0)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

const showLogin = ref(false)
const loginForm = ref({ studentId: '', email: '', password: '' })
const loginLoading = ref(false)

// 将登录状态改为响应式，避免依赖 localStorage 导致的计算属性不更新
const auth = ref(null)

const studentAuthed = computed(() => !!(auth.value && auth.value.role === 'student' && auth.value.token))
const studentProfileText = computed(() => {
  const profile = auth.value?.profile || {}
  return profile.name || profile.studentId || '已登录'
})

function formatTime(iso) {
  if (!iso) return ''
  try { return new Date(iso).toLocaleString() } catch { return String(iso) }
}

function goRegister() {
  showLogin.value = false
  router.push({ name: 'student-register' })
}

async function loadWorks() {
  loading.value.works = true
  try {
    const resp = await listExcellentWorks({ limit: 8 })
    const data = await resp.json()
    if (data.code === 0) {
      excellentWorks.value = data.data || []
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value.works = false
  }
}

async function loadCompetitions() {
  loading.value.comps = true
  try {
    const resp = await listOpenCompetitions()
    const data = await resp.json()
    if (data.code === 0) {
      openCompetitions.value = data.data || []
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value.comps = false
  }
}

async function doStudentLogin() {
  loginLoading.value = true
  try {
    const payload = { ...loginForm.value }
    if (!payload.studentId && !payload.email) {
      ElMessage.error('请填写学号或邮箱')
      return
    }
    const resp = await studentLogin(payload)
    const data = await resp.json()
    if (resp.ok && data.code === 0) {
      const payload = { token: data.data.token, role: 'student', profile: data.data.profile }
      localStorage.setItem('auth', JSON.stringify(payload))
      auth.value = payload
      ElMessage.success('登录成功')
      showLogin.value = false
    } else {
      ElMessage.error(data?.detail?.message || data?.message || '登录失败')
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('登录异常')
  } finally {
    loginLoading.value = false
  }
}

function logout() {
  try {
    const raw = localStorage.getItem('auth')
    const saved = raw ? JSON.parse(raw) : null
    if (saved?.role === 'student') {
      localStorage.removeItem('auth')
      auth.value = null
    }
  } catch {}
}

function goTeamEnroll(row) {
  if (!studentAuthed.value) {
    showLogin.value = true
    return
  }
  router.push({ name: 'team-enroll', query: { season_id: row.id } })
}

async function loadAnnouncements() {
  loading.value.ann = true
  try {
    const resp = await listAnnouncements(announcePage.value, pageSize.value)
    if (!resp.ok) throw new Error('公告接口错误')
    const data = await resp.json()
    const d = data?.data || { rows: [], total: 0 }
    announcements.value = Array.isArray(d.rows) ? d.rows : []
    total.value = Number(d.total || 0)
  } catch (e) {
    announcements.value = []
    total.value = 0
  } finally {
    loading.value.ann = false
  }
}

function prevPage() {
  if (announcePage.value > 1) {
    announcePage.value -= 1
    loadAnnouncements()
  }
}

function nextPage() {
  if (announcePage.value < totalPages.value) {
    announcePage.value += 1
    loadAnnouncements()
  }
}

onMounted(() => {
  // 初始化本地登录状态
  try {
    const raw = localStorage.getItem('auth')
    auth.value = raw ? JSON.parse(raw) : null
  } catch {}

  // 监听跨标签页登录状态变化
  window.addEventListener('storage', (e) => {
    if (e.key === 'auth') {
      try {
        auth.value = e.newValue ? JSON.parse(e.newValue) : null
      } catch {}
    }
  })

  loadWorks()
  loadCompetitions()
  loadAnnouncements()
})
</script>

<style scoped>
 .home { min-width: 1024px; min-height: 100vh; }
/* 毛玻璃头部导航 */
.home-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 32px; position: sticky; top: 0; z-index: 20; }
.glass-header { background: rgba(16, 24, 40, 0.85); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(100,160,255,0.25); }
.brand { font-family: Lora, serif; font-size: 28px; font-weight: 700; letter-spacing: 0.5px; }
.nav-links { display: flex; gap: 24px; }
.nav-links a { color: rgba(220, 232, 255, 0.78); transition: color .2s, border-color .2s; padding-bottom: 2px; border-bottom: 2px solid transparent; }
.nav-links a:hover { color: var(--accent); border-color: var(--accent); }
.actions { display: flex; align-items: center; gap: 12px; }

/* 非对称主体布局：左 2/3，右 1/3 */
 .home-content { max-width: 1600px; margin: 32px auto; padding: 0 24px; }
 .layout { display: grid; grid-template-columns: 2fr 1fr; gap: 24px; align-items: start; }
 .section { margin-bottom: 24px; animation: fadeUp .6s ease both; }
 .section h2 { font-family: Lora, serif; font-size: 32px; margin: 0 0 12px; }
 .main-left { grid-column: 1 / 2; }
 .sidebar { grid-column: 2 / 3; }

 /* 桌面断点：1600+ 宽屏四列作品，1280-1599 三列，1024-1279 两列；侧栏在 1279 以下换行 */
 @media (min-width: 1600px) {
   .works-grid { grid-template-columns: repeat(4, 1fr); }
 }
 @media (min-width: 1280px) and (max-width: 1599px) {
   .works-grid { grid-template-columns: repeat(3, 1fr); }
 }
 @media (min-width: 1024px) and (max-width: 1279px) {
   .layout { grid-template-columns: 1fr; }
   .sidebar { grid-column: 1 / -1; }
   .works-grid { grid-template-columns: repeat(2, 1fr); }
 }

/* 玻璃卡片与交互反馈 */
.glass-card { background: rgba(20, 30, 48, 0.85); backdrop-filter: blur(10px); border: 1px solid rgba(100,160,255,0.25); border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.35); transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease; }
.glass-card:hover { transform: translateY(-5px); border-color: rgba(100,255,218,0.5); box-shadow: 0 16px 40px rgba(0,0,0,0.35); }

/* 优秀作品固定三列 */
 .works-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.work-card { min-height: 160px; padding: 12px; }
.work-title { font-weight: 600; margin-bottom: 6px; }
.work-summary { color: rgba(220, 232, 255, 0.78); margin-bottom: 8px; }
.work-extra { color: rgba(255,255,255,0.55); font-size: 12px; }
.work-files { margin-top: 8px; }
.file-tag { margin-right: 8px; margin-bottom: 6px; }
.file-tag a { text-decoration: none; }
.file-tag a.disabled { pointer-events: none; color: #aaa; }

/* 右侧可视化占位 */
/* 公告卡片样式 */
.announce-card { padding: 16px; }
.announce-card .header { display: flex; align-items: center; justify-content: space-between; }
.announce-card h3 { margin: 0; font-size: 20px; }
.pager { display: flex; align-items: center; gap: 8px; }
.page-text { color: rgba(220, 232, 255, 0.75); font-size: 13px; }
.announce-list { list-style: none; padding: 0; margin: 12px 0 0; display: flex; flex-direction: column; gap: 12px; }
.announce-item { border: 1px dashed rgba(100,160,255,0.28); border-radius: 10px; padding: 10px 12px; background: rgba(16,24,40,0.6); }
.announce-item .row { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.announce-item .title { font-weight: 600; color: #e6eefc; }
.announce-item .time { color: rgba(220,232,255,0.7); font-size: 12px; }
.announce-item .content { color: rgba(220,232,255,0.82); margin: 6px 0 0; line-height: 1.5; }

/* 幽灵按钮样式 */
:deep(.el-button.ghost) { background: rgba(16,24,40,0.6); border: 1px solid var(--accent); color: var(--accent); }
:deep(.el-button.ghost:hover) { background: var(--accent); color: #0A192F; box-shadow: 0 6px 18px rgba(100,255,218,0.35); }

/* 玻璃表格 */
:deep(.el-table.glass-table) { background: var(--glass-bg); border-radius: 12px; overflow: hidden; }
:deep(.el-table.glass-table .el-table__body-wrapper) { background: transparent; }
:deep(.el-table.glass-table td), :deep(.el-table.glass-table th) { background: transparent; color: var(--text); }

/* 强化首页开放报名表格的暗色对比度与条纹可读性 */
:deep(.el-table.glass-table) {
  background: rgba(20, 30, 48, 0.85);
  border: 1px solid rgba(100,160,255,0.28);
}
:deep(.el-table.glass-table th) {
  background: rgba(16, 24, 40, 0.95);
}
/* 斑马条纹：奇偶行不同深度，提升分隔感 */
:deep(.el-table.glass-table .el-table__row:nth-child(odd) td) {
  background-color: rgba(24, 36, 60, 0.55);
}
:deep(.el-table.glass-table .el-table__row:nth-child(even) td) {
  background-color: rgba(18, 28, 48, 0.55);
}
/* 悬停高亮 */
:deep(.el-table.glass-table .el-table__row:hover td) {
  background-color: rgba(40, 60, 96, 0.75) !important;
}
/* 边框与分割线更清晰 */
:deep(.el-table.glass-table td), :deep(.el-table.glass-table th) {
  border-color: rgba(100,160,255,0.28);
}

/* 进入视口淡入上移 */
@keyframes fadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
@keyframes pulse { 0%, 100% { opacity: 0.8; } 50% { opacity: 1; } }
</style>