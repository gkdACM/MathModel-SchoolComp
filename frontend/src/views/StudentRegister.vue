<template>
  <div class="register layout">
    <header class="glass-header header">
      <div class="brand">学生注册</div>
      <div class="actions">
        <el-button @click="goHome">返回首页</el-button>
      </div>
    </header>
    <main class="content">
      <el-card class="glass-card" shadow="hover">
        <template #header>
          <div class="card-header"><span>创建学生账号</span></div>
        </template>

        <el-form label-width="120px" @submit.prevent="onSubmit">
          <el-form-item label="学号">
            <el-input v-model.trim="form.studentId" placeholder="例如：20230001" />
          </el-form-item>
          <el-form-item label="姓名">
            <el-input v-model.trim="form.name" placeholder="请输入中文姓名" />
          </el-form-item>
          <el-form-item label="学院">
            <el-input v-model.trim="form.college" placeholder="例如：数学学院" />
          </el-form-item>
          <el-form-item label="班级">
            <el-input v-model.trim="form.class" placeholder="例如：数模2201" />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model.trim="form.email" placeholder="用于验证码与找回" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" type="password" placeholder="至少6位" />
          </el-form-item>

          <div class="actions-row">
            <el-button type="primary" :disabled="loading" @click="onSubmit">注册</el-button>
            <span class="muted" v-if="error">{{ error }}</span>
            <span class="success" v-if="success">{{ success }}</span>
          </div>
        </el-form>
      </el-card>
    </main>
  </div>
  
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const form = ref({ studentId: '', name: '', college: '', class: '', email: '', password: '' })
const loading = ref(false)
const error = ref('')
const success = ref('')

function goHome() { router.push({ name: 'home' }) }

async function onSubmit() {
  error.value = ''
  success.value = ''
  const payload = { ...form.value }

  if (!payload.studentId || !payload.name || !payload.college || !payload.class || !payload.email || !payload.password) {
    error.value = '请完整填写所有字段'
    return
  }
  if (!/^[\w.-]+@([\w-]+\.)+[\w-]{2,}$/.test(payload.email)) {
    error.value = '邮箱格式不正确'
    return
  }
  if (payload.password.length < 6) {
    error.value = '密码至少6位'
    return
  }

  loading.value = true
  try {
    const { studentRegister } = await import('../api/register.js')
    const resp = await studentRegister(payload)
    if (!resp.ok) {
      error.value = `网络或服务器错误（${resp.status}）`
      return
    }
    const json = await resp.json()
    if (json.code !== 0) {
      if (json.details?.fieldErrors?.length) {
        error.value = json.details.fieldErrors[0]?.message || json.message || '参数错误'
      } else {
        error.value = json.message || '注册失败'
      }
      return
    }
    success.value = '注册成功，请使用学号或邮箱登录'
    setTimeout(() => router.push({ name: 'home' }), 1200)
  } catch (e) {
    error.value = '无法连接服务器，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.layout { min-width: 1024px; }
.header { display: flex; align-items: center; justify-content: space-between; padding: 16px 32px; }
.content { padding: 24px 32px; }
.card-header { display: flex; align-items: center; justify-content: space-between; }
.actions-row { display: flex; align-items: center; gap: 12px; }
.muted { color: #888; }
.success { color: #2ecc71; }
</style>