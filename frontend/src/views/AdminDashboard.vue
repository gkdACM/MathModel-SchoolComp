<template>
  <div class="dashboard-container">
    <header class="dashboard-header">
      <h1>管理员控制台</h1>
      <p class="sub">此为占位页面，后续将完善功能模块。</p>
      <div class="profile" v-if="auth?.profile">
        <span>当前用户：</span>
        <strong>{{ auth.profile.name || auth.profile.email || '管理员' }}</strong>
      </div>
      <button class="logout" @click="onLogout">退出登录</button>
    </header>

    <main class="dashboard-main">
      <section class="grid">
        <div class="card wide">
          <div class="header-row">
            <h2>评审与成绩</h2>
            <div class="actions">
              <select v-model="seasonId" class="sel">
                <option value="">选择赛季</option>
                <option v-for="s in seasons" :key="s.id" :value="s.id">{{ s.name }}</option>
              </select>
              <button class="btn" :disabled="!seasonId || exporting" @click="onExport">导出成绩表</button>
            </div>
          </div>
          <div class="body">
            <div class="hint">请选择赛季后查看教师评分进度，并可导出成绩表。</div>
            <div class="table-wrapper" v-if="progress.length">
              <table class="table">
                <thead>
                  <tr>
                    <th>教师账号</th>
                    <th>姓名</th>
                    <th>已评数</th>
                    <th>待评数</th>
                    <th>总提交数</th>
                    <th>完成率</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="p in progress" :key="p.teacher_id">
                    <td>{{ p.account }}</td>
                    <td>{{ p.name }}</td>
                    <td>{{ p.reviewed_count }}</td>
                    <td class="pending" :class="{warn: p.pending_count>0}">{{ p.pending_count }}</td>
                    <td>{{ p.total_submissions }}</td>
                    <td>{{ p.completion_rate }}%</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="empty" v-else>请先选择赛季，或暂无数据</div>
            <div v-if="error" class="error">{{ error }}</div>
          </div>
        </div>

        <div class="card">
          <h2>快捷入口</h2>
          <div class="quick-actions">
            <a class="btn" href="/admin/teachers/generate">批量生成教师账号</a>
            <a class="btn" href="/admin/competitions/manage">竞赛管理</a>
            <a class="btn" href="/admin/announcements">公告管理/发布公告</a>
            <a class="btn" href="/admin/audit/logs">日志中心</a>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { listCompetitions, exportScores, reviewProgress } from '../api/competitions.js'

const auth = ref(null)
onMounted(() => {
  try {
    const raw = localStorage.getItem('auth')
    auth.value = raw ? JSON.parse(raw) : null
  } catch {}
  loadSeasons()
})

function onLogout() {
  localStorage.removeItem('auth')
  // 简单跳转到登录页
  window.location.href = '/admin-manager'
}

// ------ 赛季选择与进度展示 ------
const seasons = ref([])
const seasonId = ref('')
const progress = ref([])
const error = ref('')
const exporting = ref(false)

async function loadSeasons() {
  try {
    const resp = await listCompetitions()
    if (!resp.ok) throw new Error(`http ${resp.status}`)
    const json = await resp.json()
    if (json.code !== 0) throw new Error(json.message || '获取竞赛失败')
    seasons.value = json.data || []
  } catch (e) {
    error.value = '无法获取赛季列表，请确认管理员已登录且后端可用'
  }
}

async function loadProgress() {
  error.value = ''
  progress.value = []
  if (!seasonId.value) return
  try {
    const resp = await reviewProgress(seasonId.value)
    if (!resp.ok) throw new Error(`http ${resp.status}`)
    const json = await resp.json()
    if (json.code !== 0) throw new Error(json.message || '加载进度失败')
    progress.value = json.data?.teachers || []
  } catch (e) {
    error.value = '无法加载教师进度，请检查后端服务'
  }
}

async function onExport() {
  if (!seasonId.value) return
  exporting.value = true
  try {
    const resp = await exportScores(seasonId.value)
    if (!resp.ok) throw new Error(`http ${resp.status}`)
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `scores-season-${seasonId.value}.csv`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    error.value = '导出失败，请稍后重试'
  } finally {
    exporting.value = false
  }
}

watch(seasonId, loadProgress)
</script>

<style scoped>
.dashboard-container {
  min-height: 100vh;
  background: #0b1220;
  color: #e6eefc;
  padding: 24px;
}
.dashboard-header { display: flex; align-items: center; gap: 16px; }
.dashboard-header h1 { margin: 0; font-size: 24px; }
.dashboard-header .sub { color: #9fb3d8; }
.profile { margin-left: auto; color: #cfe1ff; }
.logout { margin-left: 8px; }

.dashboard-main { margin-top: 24px; }
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.card { background: #141d33; border: 1px solid rgba(100,160,255,0.25); border-radius: 12px; padding: 16px; }
.card h2 { margin-top: 0; font-size: 18px; }
.btn { display: inline-block; padding: 8px 12px; border: 1px solid rgba(100,160,255,0.45); border-radius: 8px; color: #cfe1ff; text-decoration: none; }
.btn:hover { border-color: rgba(100,160,255,0.75); }
/* 追加样式：宽卡片、表格与动作区域 */
.card.wide { grid-column: 1 / span 3; }
.header-row { display: flex; align-items: center; justify-content: space-between; }
.actions { display: flex; align-items: center; gap: 8px; }
.sel { background: #0b1220; color: #cfe1ff; border: 1px solid rgba(100,160,255,0.45); border-radius: 8px; padding: 6px 8px; }
.table-wrapper { overflow: auto; margin-top: 12px; }
.table { width: 100%; border-collapse: collapse; }
.table th, .table td { border-bottom: 1px dashed rgba(150,180,230,0.35); padding: 8px 10px; text-align: left; }
.table .pending.warn { color: #ffb36b; font-weight: 600; }
.quick-actions { display: flex; gap: 8px; }
@media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
</style>