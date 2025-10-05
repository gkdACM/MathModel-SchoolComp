<template>
  <div class="page">
    <header class="header">
      <h1>日志中心 · 审计日志</h1>
      <p class="sub">支持按时间、角色、动作筛选，并导出为 CSV</p>
    </header>

    <section class="card filters">
      <el-form label-width="120px" @submit.prevent>
        <div class="grid">
          <el-form-item label="时间起">
            <el-date-picker v-model="start" type="datetime" placeholder="开始时间" />
          </el-form-item>
          <el-form-item label="时间止">
            <el-date-picker v-model="end" type="datetime" placeholder="结束时间" />
          </el-form-item>
          <el-form-item label="角色类型">
            <el-select v-model="actorType" clearable placeholder="全部">
              <el-option label="管理员" value="admin" />
              <el-option label="教师" value="teacher" />
              <el-option label="学生" value="student" />
            </el-select>
          </el-form-item>
          <el-form-item label="角色ID">
            <el-input v-model.trim="actorId" placeholder="可选：具体角色ID" />
          </el-form-item>
          <el-form-item label="动作">
            <el-input v-model.trim="action" placeholder="如 team.lock / scores.export" />
          </el-form-item>
          <el-form-item label="对象类型">
            <el-input v-model.trim="objectType" placeholder="如 team / competition" />
          </el-form-item>
          <el-form-item label="对象ID">
            <el-input v-model.trim="objectId" placeholder="可选：对象主键ID" />
          </el-form-item>
        </div>
        <div class="actions">
          <el-button type="primary" :loading="loading" @click="onSearch">查询</el-button>
          <el-button :loading="exporting" @click="onExport">导出 CSV</el-button>
        </div>
      </el-form>
      <el-alert v-if="error" :title="error" type="error" show-icon class="mt8" />
    </section>

    <section class="card">
      <h2>结果列表</h2>
      <div class="table-wrapper" v-if="rows.length">
        <table class="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>时间</th>
              <th>角色</th>
              <th>角色ID</th>
              <th>动作</th>
              <th>对象类型</th>
              <th>对象ID</th>
              <th>详情</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.id">
              <td>{{ r.id }}</td>
              <td>{{ formatTime(r.created_at) }}</td>
              <td>{{ r.actor_type }}</td>
              <td>{{ r.actor_id }}</td>
              <td>{{ r.action }}</td>
              <td>{{ r.object_type }}</td>
              <td>{{ r.object_id }}</td>
              <td><pre class="details">{{ formatDetails(r.details) }}</pre></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="empty" v-else>暂无数据，请调整筛选条件</div>

      <div class="pager">
        <el-pagination
          background
          layout="prev, pager, next"
          :total="total"
          :page-size="pageSize"
          :current-page="page"
          @current-change="onPageChange"
        />
      </div>
    </section>
  </div>
  
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listAuditLogs, exportAuditLogs } from '../api/audit.js'

const start = ref('')
const end = ref('')
const actorType = ref('')
const actorId = ref('')
const action = ref('')
const objectType = ref('')
const objectId = ref('')
const loading = ref(false)
const exporting = ref(false)
const error = ref('')

const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

function buildParams(extra = {}) {
  const params = { page: page.value, page_size: pageSize.value, ...extra }
  if (actorType.value) params.actor_type = actorType.value
  if (actorId.value) params.actor_id = Number(actorId.value)
  if (action.value) params.action = action.value
  if (objectType.value) params.object_type = objectType.value
  if (objectId.value) params.object_id = Number(objectId.value)
  if (start.value) params.start_time = toIso(start.value)
  if (end.value) params.end_time = toIso(end.value)
  return params
}

function toIso(v) {
  try {
    const d = new Date(v)
    if (!isNaN(d.getTime())) return d.toISOString().slice(0,19)
  } catch {}
  return ''
}

function formatTime(iso) {
  if (!iso) return ''
  try { return new Date(iso).toLocaleString() } catch { return String(iso) }
}

function formatDetails(json) {
  if (!json) return ''
  try {
    const obj = typeof json === 'string' ? JSON.parse(json) : json
    return JSON.stringify(obj, null, 2)
  } catch {
    return String(json)
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const resp = await listAuditLogs(buildParams())
    if (!resp.ok) throw new Error(`http ${resp.status}`)
    const json = await resp.json()
    if (json.code !== 0) throw new Error(json.message || '查询失败')
    rows.value = json.data?.rows || []
    total.value = json.data?.total || 0
  } catch (e) {
    error.value = '无法查询审计日志，请确认登录与后端服务'
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  load()
}

function onPageChange(p) {
  page.value = p
  load()
}

async function onExport() {
  exporting.value = true
  error.value = ''
  try {
    const resp = await exportAuditLogs(buildParams())
    if (!resp.ok) throw new Error(`http ${resp.status}`)
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'audit-logs.csv'
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

onMounted(load)
</script>

<style scoped>
.page { min-height: 100vh; background: #0b1220; color: #e6eefc; padding: 24px; }
.header { display: flex; align-items: baseline; gap: 12px; }
.header h1 { margin: 0; font-size: 22px; }
.header .sub { color: #9fb3d8; }
.card { background: #141d33; border: 1px solid rgba(100,160,255,0.25); border-radius: 12px; padding: 16px; }
.filters .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.actions { display: flex; gap: 8px; }
.mt8 { margin-top: 8px; }
.table { width: 100%; border-collapse: collapse; }
.table th, .table td { border: 1px solid rgba(100,160,255,0.25); padding: 8px; vertical-align: top; }
.table th { background: #141d33; }
.table-wrapper { overflow: auto; }
.details { white-space: pre-wrap; font-size: 12px; color: #cfe1ff; }
.empty { color: #9fb3d8; }
.pager { margin-top: 12px; display: flex; justify-content: center; }
</style>