<template>
  <div class="team-enroll layout">
    <header class="glass-header header">
      <div class="brand">队伍报名</div>
      <div class="actions">
        <el-button @click="goHome">返回首页</el-button>
      </div>
    </header>
    <main class="content">
      <el-card class="glass-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>赛季ID：{{ seasonId }}</span>
          </div>
        </template>

        <div v-if="loading" class="muted">加载中...</div>
        <div v-else>
          <div v-if="team">
            <h3>我的队伍：{{ team.name }}（编号：{{ team.team_code }}）</h3>
            <p class="muted">队长ID：{{ team.captain_id }} | 状态：{{ team.status }} | 锁定：{{ team.locked ? '是' : '否' }}</p>
            <div class="grid two">
              <div>
                <h4>成员列表</h4>
                <el-table :data="team.members" border size="small" class="glass-table">
                  <el-table-column prop="student_id" label="学号" min-width="120" />
                  <el-table-column prop="name" label="姓名" min-width="120" />
                  <el-table-column prop="role" label="角色" width="100" />
                </el-table>
              </div>
              <div>
                <h4>加入记录</h4>
                <el-table :data="team.join_requests" border size="small" class="glass-table">
                  <el-table-column prop="student_id" label="学号" min-width="120" />
                  <el-table-column prop="status" label="状态" width="120" />
                  <el-table-column prop="created_at" label="时间" min-width="160">
                    <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
                  </el-table-column>
                </el-table>
              </div>
            </div>
            <div class="token-box">
              <div v-if="team.join_token">
                <el-alert type="info" :closable="false" title="当前加入令牌">
                  <template #default>
                    <div class="token-row">
                      <code>{{ team.join_token.token }}</code>
                      <span class="muted">有效期至：{{ formatTime(team.join_token.expires_at) }}</span>
                      <el-button class="ml8" size="small" @click="copyToken(team.join_token.token)">复制</el-button>
                    </div>
                  </template>
                </el-alert>
              </div>
              <div class="mt12">
                <el-button type="primary" size="small" @click="refreshToken">生成新令牌</el-button>
              </div>
            </div>

            <!-- 作品提交区域（双文件：论文PDF + 支撑材料 RAR/ZIP/7Z） -->
            <el-divider content-position="left">作品提交（论文 + 支撑材料）</el-divider>
            <div class="submit-box">
              <el-form label-width="140px">
                <el-form-item label="论文（PDF）">
                  <input type="file" accept="application/pdf" @change="onThesisChange" />
                  <div class="muted" v-if="thesisFile">已选择：{{ thesisFile.name }}</div>
                </el-form-item>
                <el-form-item label="支撑材料（RAR/ZIP/7Z）">
                  <input type="file" accept=".zip,.rar,.7z,application/zip,application/x-rar-compressed,application/x-7z-compressed" @change="onMaterialsChange" />
                  <div class="muted" v-if="materialsFile">已选择：{{ materialsFile.name }}</div>
                </el-form-item>
                <el-form-item label="备注（可选）">
                  <el-input v-model="submitNote" placeholder="例如：第二版，修复数据清洗问题" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :disabled="!canSubmit || submitting" :loading="submitting" @click="doUpload">提交作品</el-button>
                  <span class="muted ml8">论文必须是 PDF；支撑材料支持 RAR/ZIP/7Z；截止期内允许多次提交自动版本号</span>
                </el-form-item>
                <el-alert v-if="submitError" :title="submitError" type="error" show-icon class="mt12" />
                <el-alert v-if="submitSuccess" :title="submitSuccess" type="success" show-icon class="mt12" />
              </el-form>
            </div>

            <!-- 提交记录列表（显示两文件信息） -->
            <el-divider content-position="left">提交记录</el-divider>
            <el-table :data="submissions" border size="small" class="glass-table">
              <el-table-column prop="version" label="版本" width="80" />
              <el-table-column prop="note" label="备注" min-width="160" />
              <el-table-column label="论文（PDF）" min-width="280">
                <template #default="{ row }">
                  <div v-if="row.files && row.files.thesis">
                    <div>文件名：{{ row.files.thesis.filename }}</div>
                    <div class="muted">大小：{{ formatSize(row.files.thesis.size) }} | 哈希：{{ row.files.thesis.hash }}</div>
                  </div>
                  <span v-else class="muted">未上传</span>
                </template>
              </el-table-column>
              <el-table-column label="支撑材料" min-width="280">
                <template #default="{ row }">
                  <div v-if="row.files && row.files.materials">
                    <div>文件名：{{ row.files.materials.filename }}</div>
                    <div class="muted">大小：{{ formatSize(row.files.materials.size) }} | 哈希：{{ row.files.materials.hash }}</div>
                  </div>
                  <span v-else class="muted">未上传</span>
                </template>
              </el-table-column>
              <el-table-column label="时间" min-width="180">
                <template #default="{ row }">{{ formatTime(row.uploadedAt) }}</template>
              </el-table-column>
            </el-table>
          </div>

          <div v-else class="grid two">
            <div>
              <h3>创建队伍</h3>
              <el-form :model="createForm" label-width="120px">
                <el-form-item label="队伍名称">
                  <el-input v-model="createForm.name" placeholder="例如：数学小队" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="doCreateTeam" :loading="createLoading">创建并报名</el-button>
                </el-form-item>
              </el-form>
            </div>
            <div>
              <h3>使用令牌加入队伍</h3>
              <el-form :model="joinForm" label-width="120px">
                <el-form-item label="加入令牌">
                  <el-input v-model="joinForm.token" placeholder="粘贴队长分享的令牌" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="doJoinTeam" :loading="joinLoading">加入并报名</el-button>
                </el-form-item>
              </el-form>
            </div>
          </div>
        </div>
      </el-card>
    </main>
  </div>
  
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { createTeamForSeason, getMyTeam, joinTeamByToken, generateJoinToken, uploadSubmission, listSubmissions } from '../api/student'

const route = useRoute()
const router = useRouter()
const seasonId = Number(route.query.season_id || 0)

const loading = ref(true)
const team = ref(null)
const createForm = ref({ name: '' })
const createLoading = ref(false)
const joinForm = ref({ token: '' })
const joinLoading = ref(false)
const thesisFile = ref(null)
const materialsFile = ref(null)
const submitNote = ref('')
const submitting = ref(false)
const submitError = ref('')
const submitSuccess = ref('')
const submissions = ref([])

const canSubmit = computed(() => !!thesisFile.value && !!materialsFile.value)

function formatTime(iso) {
  if (!iso) return ''
  try { return new Date(iso).toLocaleString() } catch { return String(iso) }
}

function goHome() { router.push({ name: 'home' }) }

async function loadMyTeam() {
  loading.value = true
  try {
    const resp = await getMyTeam(seasonId)
    const data = await resp.json()
    if (resp.ok && data.code === 0) {
      team.value = data.data
    } else {
      ElMessage.error(data?.detail?.message || data?.message || '加载队伍失败')
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('加载队伍异常')
  } finally {
    loading.value = false
  }
}

async function doCreateTeam() {
  if (!createForm.value.name) {
    ElMessage.error('请填写队伍名称')
    return
  }
  createLoading.value = true
  try {
    const resp = await createTeamForSeason(seasonId, { name: createForm.value.name })
    const data = await resp.json()
    if (resp.ok && data.code === 0) {
      ElMessage.success('队伍创建成功，已报名')
      team.value = data.data
    } else {
      ElMessage.error(data?.detail?.message || data?.message || '创建失败')
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('创建异常')
  } finally {
    createLoading.value = false
  }
}

async function doJoinTeam() {
  if (!joinForm.value.token) {
    ElMessage.error('请输入加入令牌')
    return
  }
  joinLoading.value = true
  try {
    const resp = await joinTeamByToken(joinForm.value.token)
    const data = await resp.json()
    if (resp.ok && data.code === 0) {
      ElMessage.success('加入成功，已报名')
      team.value = data.data
    } else {
      ElMessage.error(data?.detail?.message || data?.message || '加入失败')
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('加入异常')
  } finally {
    joinLoading.value = false
  }
}

async function refreshToken() {
  try {
    const resp = await generateJoinToken(team.value.id)
    const data = await resp.json()
    if (resp.ok && data.code === 0) {
      ElMessage.success('令牌已刷新')
      team.value.join_token = data.data
    } else {
      ElMessage.error(data?.detail?.message || data?.message || '刷新失败')
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('刷新异常')
  }
}

onMounted(() => {
  if (!seasonId) {
    ElMessage.error('缺少赛季ID')
    goHome()
    return
  }
  loadMyTeam()
})

function onThesisChange(e) {
  const f = e.target?.files?.[0]
  thesisFile.value = f || null
  // 前端校验：必须 PDF
  if (thesisFile.value) {
    const name = thesisFile.value.name.toLowerCase()
    const isPdf = name.endsWith('.pdf') || thesisFile.value.type === 'application/pdf'
    if (!isPdf) {
      ElMessage.error('论文文件必须为 PDF')
      thesisFile.value = null
    }
  }
}

function onMaterialsChange(e) {
  const f = e.target?.files?.[0]
  materialsFile.value = f || null
  // 前端校验：允许 rar/zip/7z
  if (materialsFile.value) {
    const name = materialsFile.value.name.toLowerCase()
    const ok = name.endsWith('.zip') || name.endsWith('.rar') || name.endsWith('.7z')
    if (!ok) {
      ElMessage.error('支撑材料必须为 RAR/ZIP/7Z 格式')
      materialsFile.value = null
    }
  }
}

async function doUpload() {
  submitError.value = ''
  submitSuccess.value = ''
  if (!team.value?.id) {
    ElMessage.error('尚未创建或加入队伍')
    return
  }
  if (!thesisFile.value) {
    ElMessage.error('请选择论文（PDF）')
    return
  }
  if (!materialsFile.value) {
    ElMessage.error('请选择支撑材料（RAR/ZIP/7Z）')
    return
  }
  submitting.value = true
  try {
    const resp = await uploadSubmission(team.value.id, thesisFile.value, materialsFile.value, submitNote.value)
    const data = await resp.json()
    if (resp.ok && data.code === 0) {
      submitSuccess.value = `提交成功：版本 ${data.data.version}`
      thesisFile.value = null
      materialsFile.value = null
      submitNote.value = ''
      await loadSubmissions()
    } else {
      submitError.value = data?.detail?.message || data?.message || '提交失败'
    }
  } catch (e) {
    console.error(e)
    submitError.value = '提交异常'
  } finally {
    submitting.value = false
  }
}

async function loadSubmissions() {
  if (!team.value?.id) return
  try {
    const resp = await listSubmissions(team.value.id)
    const data = await resp.json()
    if (resp.ok && data.code === 0) {
      const rows = (data.data || []).map(r => {
        const filesArr = Array.isArray(r.files) ? r.files : []
        const filesByType = {}
        for (const f of filesArr) {
          if (f && f.type) filesByType[f.type] = f
        }
        return { ...r, files: filesByType }
      })
      submissions.value = rows
    } else {
      submissions.value = []
    }
  } catch (e) {
    console.error(e)
    submissions.value = []
  }
}

// 每次 team 变化后加载提交记录
watch(team, (nv) => { if (nv?.id) loadSubmissions() })

function formatSize(bytes) {
  if (!bytes && bytes !== 0) return ''
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let idx = 0
  while (size >= 1024 && idx < units.length - 1) { size /= 1024; idx++ }
  return `${size.toFixed(1)} ${units[idx]}`
}
</script>

<style scoped>
.header { display: flex; align-items: center; justify-content: space-between; padding: 12px 24px; }
.content { padding: 24px; }
.grid.two { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.muted { color: var(--muted); }
.token-row { display: flex; align-items: center; gap: 12px; }
.ml8 { margin-left: 8px; }
.mt12 { margin-top: 12px; }
</style>