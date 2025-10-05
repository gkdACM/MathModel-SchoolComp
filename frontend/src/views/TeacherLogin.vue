<template>
  <div class="page-container" role="main">
    <div class="content-wrapper">
      <section class="login-panel" aria-label="教师登录">
        <div class="login-card">
          <h2 class="login-title">教师登录</h2>
          <p class="login-subtitle">Teacher Console</p>

          <el-form class="login-form" label-position="top" @submit.prevent="onSubmit">
            <el-form-item label="教师账号">
              <el-input
                v-model.trim="account"
                :disabled="loading"
                placeholder="例如 t001"
                autocomplete="username"
                clearable
              />
            </el-form-item>

            <el-form-item label="密码">
              <el-input
                v-model="password"
                type="password"
                :disabled="loading"
                placeholder="登录密码"
                autocomplete="current-password"
                show-password
              />
            </el-form-item>

            <div class="actions-row">
              <el-button type="primary" :loading="loading" :disabled="!canSubmit" @click="onSubmit">登录</el-button>
              <span class="error" v-if="error">{{ error }}</span>
            </div>
          </el-form>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const account = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const canSubmit = computed(() => account.value.trim().length > 0 && password.value.length > 0)

async function onSubmit() {
  error.value = ''
  if (!canSubmit.value) {
    error.value = '请填写完整账号与密码'
    return
  }
  loading.value = true
  try {
    const { teacherLogin } = await import('../api/auth.js')
    const resp = await teacherLogin({ account: account.value.trim(), password: password.value })
    if (!resp.ok) {
      if (resp.status === 404) {
        error.value = '接口未找到：请确认后端已实现 /api/auth/teacher-login 或正确配置代理域名'
      } else if (resp.status === 401) {
        error.value = '认证失败：请检查账号或密码'
      } else {
        error.value = `网络错误（${resp.status}）：请稍后重试`
      }
      return
    }
    const json = await resp.json()
    if (json.code !== 0) {
      error.value = json.message || '登录失败'
      return
    }
    const { token, role, profile } = json.data || {}
    if (role !== 'teacher') {
      error.value = '该账号非教师角色'
      return
    }
    const authPayload = { token, role, profile }
    localStorage.setItem('auth', JSON.stringify(authPayload))
    // 登录成功后跳转：如有指定教师控制台路由，可替换为 /teacher-dashboard
    const params = new URLSearchParams(window.location.search)
    const redirect = params.get('redirect')
    // 默认跳转到教师控制台，而非站点首页
    const target = redirect || '/teacher'
    window.location.href = target
  } catch (e) {
    error.value = '无法连接服务器：请确认后端服务已启动并配置 Vite 代理'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page-container { min-height: 100vh; display: grid; place-items: center; background-color: #0b1220; color: #eef2f8; }
.content-wrapper { width: 100%; max-width: 960px; padding: 24px; display: grid; place-items: center; }
.login-card { width: 420px; border-radius: 12px; padding: 24px; background: rgba(20, 30, 48, 0.7); box-shadow: 0 6px 24px rgba(0,0,0,0.2); }
.login-title { margin: 0; font-size: 22px; font-weight: 600; }
.login-subtitle { margin: 6px 0 16px; font-size: 13px; color: #a6b3c6; }
.actions-row { display: flex; align-items: center; gap: 12px; }
.error { color: #ff6b6b; }
</style>