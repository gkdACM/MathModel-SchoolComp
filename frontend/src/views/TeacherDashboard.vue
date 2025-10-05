<template>
  <div class="page">
    <h2>教师控制台</h2>
    <p>请选择要评审的竞赛：</p>
    <div class="list">
      <el-card v-for="c in competitions" :key="c.id" class="card">
        <div class="row">
          <div class="info">
            <div class="name">{{ c.name }}</div>
            <div class="meta">状态：{{ c.status }} | 评审期：{{ c.review_start }} - {{ c.review_end }}</div>
          </div>
          <el-button type="primary" @click="enter(c.id)">进入作品列表</el-button>
        </div>
      </el-card>
    </div>
    <div v-if="error" class="error">{{ error }}</div>
  </div>
 </template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const competitions = ref([])
const error = ref('')

async function load() {
  try {
    const { listCompetitions } = await import('../api/teacher.js')
    const resp = await listCompetitions()
    if (!resp.ok) throw new Error(`http ${resp.status}`)
    const json = await resp.json()
    if (json.code !== 0) throw new Error(json.message || '加载失败')
    competitions.value = json.data || []
  } catch (e) {
    error.value = '无法加载竞赛列表，请确认已登录教师账号并后端服务可用'
  }
}

function enter(seasonId) {
  router.push({ name: 'teacher-submissions', params: { seasonId } })
}

onMounted(load)
</script>

<style scoped>
.page { padding: 24px; }
.list { display: grid; gap: 12px; grid-template-columns: 1fr; }
.card { }
.row { display: flex; justify-content: space-between; align-items: center; }
.name { font-weight: 600; }
.meta { font-size: 12px; color: #666; }
.error { color: #e74c3c; margin-top: 12px; }
</style>