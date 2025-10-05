<template>
  <div class="page">
    <header class="header">
      <h1>公告管理</h1>
      <p class="sub">创建、编辑、置顶与删除公告</p>
      <div class="actions">
        <el-button type="primary" @click="onCreate">新建公告</el-button>
      </div>
    </header>

    <main class="main">
      <el-table :data="rows" border size="small" class="glass-table">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="publishedAt" label="发布时间" width="200">
          <template #default="{ row }">{{ formatTime(row.publishedAt) }}</template>
        </el-table-column>
        <el-table-column prop="pinned" label="置顶" width="100">
          <template #default="{ row }">
            <el-tag :type="row.pinned ? 'success' : 'info'">{{ row.pinned ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240">
          <template #default="{ row }">
            <el-button class="ghost" size="small" @click="onEdit(row)">编辑</el-button>
            <el-button class="ghost" size="small" type="danger" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          background
          layout="prev, pager, next"
          :page-size="pageSize"
          :total="total"
          :current-page="page"
          @current-change="onPage"
        />
      </div>
    </main>

    <el-dialog v-model="showDialog" :title="isEditing ? '编辑公告' : '新建公告'" width="640px">
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model.trim="form.title" placeholder="请输入标题" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input type="textarea" v-model="form.content" placeholder="请输入内容" :rows="6" />
        </el-form-item>
        <el-form-item label="发布时间">
          <el-date-picker v-model="form.publishedAt" type="datetime" placeholder="默认当前时间" style="width: 100%" />
        </el-form-item>
        <el-form-item label="置顶">
          <el-switch v-model="form.pinned" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listAdminAnnouncements, createAdminAnnouncement, updateAdminAnnouncement, deleteAdminAnnouncement } from '../api/adminAnnouncements'

const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const rows = ref([])

const showDialog = ref(false)
const isEditing = ref(false)
const editingId = ref(null)
const saving = ref(false)
const form = ref({ title: '', content: '', publishedAt: null, pinned: false })

function formatTime(iso) { try { return iso ? new Date(iso).toLocaleString() : '' } catch { return String(iso||'') } }

async function load() {
  try {
    const resp = await listAdminAnnouncements(page.value, pageSize.value)
    const json = await resp.json()
    const d = json?.data || { rows: [], total: 0 }
    rows.value = Array.isArray(d.rows) ? d.rows : []
    total.value = Number(d.total || 0)
  } catch (e) {
    rows.value = []
    total.value = 0
  }
}

function onPage(p) { page.value = p; load() }

function onCreate() {
  isEditing.value = false
  editingId.value = null
  showDialog.value = true
  form.value = { title: '', content: '', publishedAt: null, pinned: false }
}

function onEdit(row) {
  isEditing.value = true
  editingId.value = row.id
  showDialog.value = true
  form.value = { title: row.title, content: row.content, publishedAt: row.publishedAt, pinned: !!row.pinned }
}

async function onSave() {
  if (!form.value.title?.trim() || !form.value.content?.trim()) return
  saving.value = true
  try {
    const payload = { title: form.value.title.trim(), content: form.value.content.trim(), pinned: !!form.value.pinned }
    if (form.value.publishedAt) payload.published_at = new Date(form.value.publishedAt).toISOString()
    let resp
    if (isEditing.value && editingId.value) resp = await updateAdminAnnouncement(editingId.value, payload)
    else resp = await createAdminAnnouncement(payload)
    const json = await resp.json()
    if (json.code === 0) { showDialog.value = false; load() }
  } finally { saving.value = false }
}

async function onDelete(row) {
  if (!confirm(`确认删除公告「${row.title}」？`)) return
  try { await deleteAdminAnnouncement(row.id); load() } catch {}
}

onMounted(load)
</script>

<style scoped>
.page { min-height: 100vh; background: #0b1220; color: #e6eefc; padding: 24px; }
.header { display: flex; align-items: baseline; gap: 12px; }
.header h1 { margin: 0; font-size: 22px; }
.header .sub { color: #9fb3d8; }
.actions { margin-left: auto; }
.main { margin-top: 16px; }
.pager { display: flex; justify-content: center; margin-top: 12px; }
/* 复用玻璃表格样式 */
:deep(.el-table.glass-table) { background: rgba(20, 30, 48, 0.85); border: 1px solid rgba(100,160,255,0.28); border-radius: 12px; }
</style>