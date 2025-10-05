<template>
  <div class="page">
    <h2>竞赛作品列表</h2>
    <div class="grid">
      <el-card v-for="s in submissions" :key="s.id" class="card">
        <div class="card-row">
          <div>
            <div class="title">队伍ID：{{ s.team_id }}（版本 {{ s.version }}）</div>
            <div class="meta">提交时间：{{ s.uploaded_at }}</div>
          </div>
          <div>
            <el-tag :type="s.reviewed ? 'success' : 'info'">{{ s.reviewed ? '已评分' : '未评分' }}</el-tag>
          </div>
        </div>
        <div class="files">
          <div v-for="f in s.files" :key="f.id" class="file-row">
            <span>{{ f.type }}：{{ f.filename }}（{{ formatSize(f.size) }}）</span>
            <el-button v-if="f.previewUrl" size="small" @click="openDetail(s.id, f.id)">查看并评分</el-button>
          </div>
        </div>
      </el-card>
    </div>
    <div v-if="error" class="error">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const submissions = ref([])
const error = ref('')

function formatSize(size) {
  if (!size || size < 0) return '0B'
  const units = ['B', 'KB', 'MB', 'GB']
  let idx = 0
  let val = size
  while (val >= 1024 && idx < units.length - 1) {
    val = val / 1024
    idx++
  }
  return `${val.toFixed(1)}${units[idx]}`
}

async function load() {
  try {
    const seasonId = route.params.seasonId
    const { listSubmissions } = await import('../api/teacher.js')
    const resp = await listSubmissions(seasonId)
    if (!resp.ok) throw new Error(`http ${resp.status}`)
    const json = await resp.json()
    if (json.code !== 0) throw new Error(json.message || '加载失败')
    submissions.value = json.data || []
  } catch (e) {
    error.value = '无法加载作品列表，请确认后端服务与权限'
  }
}

function openDetail(submissionId, fileId) {
  router.push({ name: 'teacher-submission-detail', params: { submissionId }, query: { fileId } })
}

onMounted(load)
</script>

<style scoped>
.page { padding: 24px; }
.grid { display: grid; gap: 12px; grid-template-columns: 1fr 1fr; }
.card { }
.card-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.title { font-weight: 600; }
.meta { font-size: 12px; color: #666; }
.files { display: grid; gap: 6px; }
.file-row { display: flex; justify-content: space-between; align-items: center; }
.error { color: #e74c3c; margin-top: 12px; }
</style>