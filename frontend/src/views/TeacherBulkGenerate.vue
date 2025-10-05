<template>
  <div class="page" role="main">
    <header class="header">
      <h1>批量生成教师账号</h1>
      <p class="sub">按行输入教师中文姓名，提交后由后端自动生成账号与初始密码</p>
    </header>

    <main class="main">
      <el-form class="form" label-position="top" @submit.prevent="onSubmit">
        <el-form-item label="教师姓名列表（每行一个中文姓名）">
          <el-input
            v-model="namesText"
            type="textarea"
            :rows="12"
            placeholder="例如：\n张三\n李四\n王五\n……"
            :disabled="loading"
          />
        </el-form-item>

        <div class="actions">
          <el-button type="primary" :disabled="!canSubmit || loading" :loading="loading" native-type="submit">生成账号</el-button>
          <el-button :disabled="loading" @click="onClear">清空</el-button>
          <el-button :disabled="loading" @click="onInitPasswords">初始化全部教师密码</el-button>
          <el-button :disabled="loading" @click="onExportCsv">导出密码CSV</el-button>
        </div>

        <el-alert v-if="error" :title="error" type="error" show-icon class="mt8" />
        <el-alert v-if="success" :title="success" type="success" show-icon class="mt8" />

        <section v-if="result && result.length" class="result">
          <h2>生成结果</h2>
          <table class="table">
            <thead>
              <tr>
                <th>姓名</th>
                <th>账号</th>
                <th>初始密码</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row,i) in result" :key="i">
                <td>{{ row.name }}</td>
                <td>{{ row.account }}</td>
                <td>{{ row.tempPassword }}</td>
                <td>{{ row.status || 'ok' }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </el-form>
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const namesText = ref('')
const loading = ref(false)
const error = ref('')
const success = ref('')
const result = ref([])

const canSubmit = computed(() => {
  const lines = namesText.value.split(/\n+/).map(s => s.trim()).filter(Boolean)
  return lines.length > 0
})

function onClear() {
  namesText.value = ''
  error.value = ''
  success.value = ''
  result.value = []
}

async function onSubmit() {
  error.value = ''
  success.value = ''
  result.value = []

  const lines = namesText.value.split(/\n+/).map(s => s.trim()).filter(Boolean)
  // 简单中文校验（基本排除空白与纯英文），允许包含中文全名及少量符号
  const invalid = lines.find(n => !/[\u4e00-\u9fa5]/.test(n))
  if (invalid) {
    error.value = `姓名必须为中文，发现异常输入：${invalid}`
    return
  }

  loading.value = true
  try {
    // 调用前端 API 方法（稍后实现），统一域名配置
    const { generateTeachers } = await import('../api/teachers.js')
    const resp = await generateTeachers({ names: lines })
    if (!resp.ok) {
      error.value = `网络错误（${resp.status}）：请稍后重试或检查登录状态`
      return
    }
    const json = await resp.json()
    if (json.code !== 0) {
      error.value = json.message || '生成失败'
      return
    }
    const rows = json.data?.rows || []
    result.value = rows
    success.value = `生成成功：${rows.length} 条`
  } catch (e) {
    error.value = '无法连接服务器：请确认后端服务与接口路径'
  } finally {
    loading.value = false
  }
}

async function onInitPasswords() {
  error.value = ''
  success.value = ''
  loading.value = true
  try {
    const { initTeacherPasswords } = await import('../api/teachers.js')
    const resp = await initTeacherPasswords({ all: true })
    if (!resp.ok) {
      error.value = `网络错误（${resp.status}）：请稍后重试或检查登录状态`
      return
    }
    const json = await resp.json()
    if (json.code !== 0) {
      error.value = json.message || '初始化失败'
      return
    }
    success.value = `已初始化 ${json.data?.updated || 0} 位教师密码为默认值 ${json.data?.defaultPassword}`
  } catch (e) {
    error.value = '无法连接服务器：请确认后端服务与接口路径'
  } finally {
    loading.value = false
  }
}

async function onExportCsv() {
  error.value = ''
  success.value = ''
  loading.value = true
  try {
    const { exportTeacherPasswords } = await import('../api/teachers.js')
    const resp = await exportTeacherPasswords()
    if (!resp.ok) {
      error.value = `网络错误（${resp.status}）：请稍后重试或检查登录状态`
      return
    }
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'teachers-passwords.csv'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    success.value = 'CSV 已下载（仅显示默认密码）'
  } catch (e) {
    error.value = '无法连接服务器：请确认后端服务与接口路径'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page { min-height: 100vh; background: #0b1220; color: #e6eefc; padding: 24px; }
.header { display: flex; align-items: baseline; gap: 12px; }
.header h1 { margin: 0; font-size: 22px; }
.header .sub { color: #9fb3d8; }
.main { margin-top: 16px; }
.form { max-width: 880px; }
.actions { display: flex; gap: 8px; }
.mt8 { margin-top: 8px; }
.result { margin-top: 16px; }
.table { width: 100%; border-collapse: collapse; }
.table th, .table td { border: 1px solid rgba(100,160,255,0.25); padding: 8px; }
.table th { background: #141d33; }
</style>