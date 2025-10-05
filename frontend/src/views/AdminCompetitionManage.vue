<template>
  <div class="page">
    <header class="header">
      <h1>竞赛管理</h1>
      <p class="sub">创建竞赛与上传赛题ZIP（覆盖保存）</p>
    </header>

    <main class="main">
      <section class="card left-col">
        <h2>创建竞赛</h2>
        <el-form label-width="120px" class="form" @submit.prevent>
          <el-form-item label="竞赛名称">
            <el-input v-model.trim="form.name" placeholder="如：2025校赛"></el-input>
          </el-form-item>
          <el-form-item label="开始时间">
            <el-date-picker v-model="form.start_time" type="datetime" placeholder="选择开始时间" />
          </el-form-item>
          <el-form-item label="结束时间">
            <el-date-picker v-model="form.end_time" type="datetime" placeholder="选择结束时间" />
          </el-form-item>
          <el-form-item label="开放报名">
            <el-checkbox v-model="form.allow_signup">创建后即开放报名（或随时可切换）</el-checkbox>
          </el-form-item>
          <div class="actions">
            <el-button type="primary" :disabled="creating" :loading="creating" @click="onCreate">创建竞赛</el-button>
          </div>
          <el-alert v-if="error" :title="error" type="error" show-icon class="mt8" />
          <el-alert v-if="success" :title="success" type="success" show-icon class="mt8" />
        </el-form>
  </section>

      <section class="card left-col">
        <h2>上传赛题ZIP</h2>
        <el-form label-width="120px" class="form" @submit.prevent>
          <el-form-item label="选择竞赛">
            <el-input v-model.number="uploadSeasonId" placeholder="输入创建后的竞赛ID"></el-input>
          </el-form-item>
          <el-form-item label="选择文件">
            <input type="file" accept=".zip" @change="onFileChange" />
          </el-form-item>
          <div class="actions">
            <el-button type="primary" :disabled="uploading || !canUpload" :loading="uploading" @click="onUpload">上传ZIP并覆盖</el-button>
          </div>
          <el-alert v-if="errorUpload" :title="errorUpload" type="error" show-icon class="mt8" />
          <el-alert v-if="successUpload" :title="successUpload" type="success" show-icon class="mt8" />
        </el-form>
  </section>

  <section class="card right-col">
    <h2>已有竞赛</h2>
    <p class="sub">点击条目可将ID填充到上传区域</p>
    <div class="list">
      <div
        v-for="s in seasons"
        :key="s.id"
        class="item"
        @click="uploadSeasonId = s.id"
        title="点击填充到上方上传区域"
      >
        <span class="sid">#{{ s.id }}</span>
        <span class="sname">{{ s.name }}</span>
        <span class="toggle">
          <el-tag :type="s.allow_signup ? 'success' : 'info'" size="small">{{ s.allow_signup ? '报名开放' : '报名关闭' }}</el-tag>
          <el-switch
            v-model="s.allow_signup"
            class="ml8"
            @click.stop
            @change="onToggleSignup(s)"
          />
        </span>
      </div>
      <div v-if="seasons.length === 0" class="empty">暂无竞赛</div>
    </div>
    <el-alert v-if="seasonsError" :title="seasonsError" type="error" show-icon class="mt8" />
  </section>
  
  <section class="card left-col">
    <h2>上传历年优秀作品</h2>
    <el-form label-width="120px" class="form" @submit.prevent>
      <el-form-item label="选择竞赛">
        <el-input v-model.number="excellentSeasonId" placeholder="输入竞赛ID"></el-input>
      </el-form-item>
      <el-form-item label="作品文件">
        <input type="file" accept=".zip,.pdf" @change="onExcellentFileChange" />
      </el-form-item>
      <el-form-item label="摘要（可选）">
        <el-input v-model.trim="excellentSummary" placeholder="作品摘要"></el-input>
      </el-form-item>
      <el-form-item label="评分（可选）">
        <el-input v-model.number="excellentScore" type="number" placeholder="评分（如：95.5）"></el-input>
      </el-form-item>
      <el-form-item label="允许下载">
        <el-checkbox v-model="excellentAllowDownload">允许从前台下载</el-checkbox>
      </el-form-item>
      <div class="actions">
        <el-button type="primary" :disabled="uploadingExcellent || !canUploadExcellent" :loading="uploadingExcellent" @click="onUploadExcellent">上传优秀作品</el-button>
      </div>
      <el-alert v-if="errorExcellent" :title="errorExcellent" type="error" show-icon class="mt8" />
      <el-alert v-if="successExcellent" :title="successExcellent" type="success" show-icon class="mt8" />
    </el-form>
  </section>
</main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const form = ref({ name: '', start_time: '', end_time: '', allow_signup: false })
const creating = ref(false)
const error = ref('')
const success = ref('')

async function onCreate() {
  error.value = ''
  success.value = ''
  if (!form.value.name || !form.value.start_time || !form.value.end_time) {
    error.value = '请填写名称、开始与结束时间'
    return
  }
  creating.value = true
  try {
    const { createCompetition } = await import('../api/competitions.js')
    const payload = {
      name: form.value.name,
      start_time: new Date(form.value.start_time).toISOString(),
      end_time: new Date(form.value.end_time).toISOString(),
      allow_signup: !!form.value.allow_signup,
    }
    const resp = await createCompetition(payload)
    if (!resp.ok) {
      error.value = `网络错误（${resp.status}）`
      return
    }
    const json = await resp.json()
    if (json.code !== 0) {
      error.value = json.message || '创建失败'
      return
    }
    success.value = `创建成功：ID=${json.data?.season?.id}`
    // 将创建的 season id 回填到上传区域，提升操作流畅度
    uploadSeasonId.value = json.data?.season?.id || ''
  } catch (e) {
    error.value = '无法连接服务器：请确认后端服务'
  } finally {
    creating.value = false
  }
}

const uploadSeasonId = ref('')
const uploadFile = ref(null)
const uploading = ref(false)
const errorUpload = ref('')
const successUpload = ref('')

function onFileChange(e) {
  const f = e.target.files?.[0]
  uploadFile.value = f || null
}

const canUpload = computed(() => !!uploadSeasonId.value && !!uploadFile.value)

async function onUpload() {
  errorUpload.value = ''
  successUpload.value = ''
  if (!canUpload.value) {
    errorUpload.value = '请先选择竞赛并选择ZIP文件'
    return
  }
  uploading.value = true
  try {
    const { uploadCompetitionZip } = await import('../api/competitions.js')
    const resp = await uploadCompetitionZip(Number(uploadSeasonId.value), uploadFile.value)
    if (!resp.ok) {
      errorUpload.value = `网络错误（${resp.status}）`
      return
    }
    const json = await resp.json()
    if (json.code !== 0) {
      errorUpload.value = json.message || '上传失败'
      return
    }
    successUpload.value = `上传成功：${json.data?.filename}（${json.data?.size}字节）`
  } catch (e) {
    errorUpload.value = '无法连接服务器：请确认后端服务'
  } finally {
    uploading.value = false
  }
}

// 竞赛列表展示
const seasons = ref([])
const seasonsError = ref('')
const seasonsLoading = ref(false)

async function fetchSeasons() {
  seasonsError.value = ''
  seasonsLoading.value = true
  try {
    const { listCompetitions } = await import('../api/competitions.js')
    const resp = await listCompetitions()
    if (!resp.ok) {
      seasonsError.value = `网络错误（${resp.status}）`
      seasons.value = []
      return
    }
    const json = await resp.json()
    if (json.code !== 0) {
      seasonsError.value = json.message || '获取竞赛列表失败'
      seasons.value = []
      return
    }
    seasons.value = json.data || []
  } catch (e) {
    seasonsError.value = '无法连接服务器：请确认后端服务'
    seasons.value = []
  } finally {
    seasonsLoading.value = false
  }
}

onMounted(() => {
  fetchSeasons()
})

async function onToggleSignup(s) {
  try {
    const { toggleSignup } = await import('../api/competitions.js')
    const resp = await toggleSignup(s.id, s.allow_signup)
    if (!resp.ok) {
      ElMessage.error(`切换失败：${resp.status}`)
      s.allow_signup = !s.allow_signup
      return
    }
    const json = await resp.json()
    if (json.code !== 0) {
      ElMessage.error(json.message || '切换失败')
      s.allow_signup = !s.allow_signup
      return
    }
    ElMessage.success(`报名已${s.allow_signup ? '开放' : '关闭'}`)
  } catch (e) {
    ElMessage.error('无法连接服务器')
    s.allow_signup = !s.allow_signup
  }
}

// --------- 历年优秀作品上传交互 ---------
const excellentSeasonId = ref('')
const excellentFile = ref(null)
const excellentSummary = ref('')
const excellentScore = ref(null)
const excellentAllowDownload = ref(false)
const uploadingExcellent = ref(false)
const errorExcellent = ref('')
const successExcellent = ref('')

function onExcellentFileChange(e) {
  const f = e.target.files?.[0]
  excellentFile.value = f || null
}

const canUploadExcellent = computed(() => !!excellentSeasonId.value && !!excellentFile.value)

async function onUploadExcellent() {
  errorExcellent.value = ''
  successExcellent.value = ''
  if (!canUploadExcellent.value) {
    errorExcellent.value = '请先选择竞赛并选择ZIP或PDF文件'
    return
  }
  uploadingExcellent.value = true
  try {
    const { uploadExcellentWork } = await import('../api/competitions.js')
    const resp = await uploadExcellentWork(Number(excellentSeasonId.value), excellentFile.value, {
      summary: excellentSummary.value || undefined,
      score: excellentScore.value ?? undefined,
      allow_download: excellentAllowDownload.value,
    })
    if (!resp.ok) {
      errorExcellent.value = `网络错误（${resp.status}）`
      return
    }
    const json = await resp.json()
    if (json.code !== 0) {
      errorExcellent.value = json.message || '上传失败'
      return
    }
    successExcellent.value = `上传成功：${json.data?.filename}（${json.data?.size}字节）`
    // 重置输入
    excellentFile.value = null
    excellentSummary.value = ''
    excellentScore.value = null
    excellentAllowDownload.value = false
  } catch (e) {
    errorExcellent.value = '无法连接服务器：请确认后端服务'
  } finally {
    uploadingExcellent.value = false
  }
}
</script>

<style scoped>
.page { min-height: 100vh; background: #0b1220; color: #e6eefc; padding: 24px; }
.header { display: flex; align-items: baseline; gap: 12px; }
.header h1 { margin: 0; font-size: 22px; }
.header .sub { color: #9fb3d8; }
.main { margin-top: 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.card { background: #141d33; border: 1px solid rgba(100,160,255,0.25); border-radius: 12px; padding: 16px; }
.form { max-width: 880px; }
.actions { display: flex; gap: 8px; }
.mt8 { margin-top: 8px; }
.left-col { grid-column: 1; }
.right-col { grid-column: 2; align-self: start; }
.list { display: flex; flex-direction: column; gap: 8px; }
.item { display: flex; gap: 10px; align-items: center; padding: 8px 10px; border: 1px dashed rgba(150,180,230,0.35); border-radius: 8px; cursor: pointer; }
.item:hover { background: rgba(100,160,255,0.12); }
.sid { color: #9fb3d8; }
.sname { color: #e6eefc; font-weight: 500; }
.toggle { display: flex; align-items: center; gap: 8px; }
.ml8 { margin-left: 8px; }
.empty { color: #9fb3d8; }
</style>