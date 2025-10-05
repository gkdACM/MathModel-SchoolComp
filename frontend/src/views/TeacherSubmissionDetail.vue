<template>
  <div class="page">
    <h2>作品详情与评分</h2>
    <div class="layout">
      <div class="preview">
        <iframe v-if="pdfUrl" :src="pdfUrl" title="论文预览" class="pdf"></iframe>
        <div v-else class="placeholder">未找到PDF预览</div>
      </div>
      <div class="score">
        <el-form :model="form" label-width="100px">
          <el-form-item label="总分">
            <el-input-number v-model="form.total" :min="0" :max="100" />
          </el-form-item>
          <el-form-item label="评语">
            <el-input v-model="form.comment" type="textarea" rows="6" placeholder="可选" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="submit">提交评分</el-button>
            <el-button @click="back">返回列表</el-button>
          </el-form-item>
          <div v-if="error" class="error">{{ error }}</div>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const pdfUrl = ref('')
const loading = ref(false)
const error = ref('')
const form = ref({ total: 0, comment: '' })

let blobUrl = ''
async function load() {
  const submissionId = route.params.submissionId
  const fileId = route.query.fileId
  const { previewPdf } = await import('../api/teacher.js')
  const url = await previewPdf(submissionId, fileId)
  console.debug('[TeacherSubmissionDetail] preview URL:', url, { submissionId, fileId })
  try {
    // 同步附带鉴权头，防止后端拒绝 query token
    let authHeader = {}
    try {
      const raw = localStorage.getItem('auth')
      const auth = raw ? JSON.parse(raw) : null
      if (auth?.token) authHeader = { Authorization: `Bearer ${auth.token}` }
    } catch {}
    const resp = await fetch(url, { headers: { Accept: 'application/pdf', ...authHeader } })
    const ct = resp.headers.get('content-type') || ''
    console.debug('[TeacherSubmissionDetail] fetch status:', resp.status, 'content-type:', ct)
    if (!resp.ok || !ct.includes('application/pdf')) {
      // 非 PDF 响应（例如 HTML 错页），避免设置到 iframe 导致递归
      pdfUrl.value = ''
      return
    }
    const blob = await resp.blob()
    blobUrl = URL.createObjectURL(blob)
    pdfUrl.value = blobUrl
  } catch (e) {
    console.error('[TeacherSubmissionDetail] fetch error:', e)
    // 请求失败（后端未启动或网络错误），不设置 iframe，显示占位
    pdfUrl.value = ''
  }
}

onUnmounted(() => {
  if (blobUrl) URL.revokeObjectURL(blobUrl)
})

async function submit() {
  try {
    loading.value = true
    const submissionId = route.params.submissionId
    const { submitScore } = await import('../api/teacher.js')
    // 后端接口字段为 score，之前发送 total 会导致 422
    const resp = await submitScore(submissionId, { score: form.value.total, comment: form.value.comment })
    if (!resp.ok) throw new Error(`http ${resp.status}`)
    const json = await resp.json()
    if (json.code !== 0) throw new Error(json.message || '提交失败')
    router.back()
  } catch (e) {
    error.value = e.message || '提交评分失败'
  } finally {
    loading.value = false
  }
}

function back() {
  router.back()
}

onMounted(load)
</script>

<style scoped>
.page { padding: 24px; }
.layout { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; }
.preview { height: 80vh; }
.pdf { width: 100%; height: 100%; border: 1px solid #ddd; }
.placeholder { display: flex; align-items: center; justify-content: center; height: 100%; color: #999; }
.error { color: #e74c3c; margin-top: 12px; }
</style>