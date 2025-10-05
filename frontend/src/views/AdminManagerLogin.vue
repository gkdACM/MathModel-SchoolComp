<template>
  <div class="page-container" role="main">
    <div class="content-wrapper">
      <!-- 左侧：系统介绍 -->
      <section class="intro-panel" aria-label="系统介绍">
        <h1 class="system-title">数学建模校赛管理系统</h1>
        <p class="system-subtitle">以数据驱动管理 · 以模型引领创新</p>
        <div class="features" aria-label="系统特性">
          <div class="feature-item">一体化竞赛流程</div>
          <div class="feature-item">公平可追溯评审</div>
          <div class="feature-item">自定义评分体系</div>
        </div>
      </section>

      <!-- 右侧：登录卡片 -->
      <section class="login-panel" aria-label="管理员登录">
        <div class="login-card">
          <h2 class="login-title">管理员登录</h2>
          <p class="login-subtitle">Admin Console</p>

          <el-form class="login-form" label-position="top" @submit.prevent="onSubmit">
            <el-form-item label="管理员账号">
              <el-input
                v-model.trim="account"
                :disabled="loading"
                placeholder="邮箱或指定用户名"
                autocomplete="username"
                clearable
                :prefix-icon="User"
              />
            </el-form-item>

            <el-form-item label="密码">
              <el-input
                v-model="password"
                type="password"
                :disabled="loading"
                placeholder="请输入密码"
                autocomplete="current-password"
                show-password
                :prefix-icon="Lock"
              />
            </el-form-item>

            <el-alert v-if="error" :title="error" type="error" show-icon center class="error-alert" />

            <el-form-item>
              <el-button
                class="submit-button"
                type="primary"
                :disabled="!canSubmit || loading"
                :loading="loading"
                native-type="submit"
              >安全登录</el-button>
            </el-form-item>

            <div class="aux-actions">
              <el-link type="primary" :underline="false" :disabled="loading" @click="onForgot">忘记密码</el-link>
            </div>
          </el-form>

          <p class="footer-note">仅限PC端 · 推荐分辨率 1920×1080</p>
        </div>
      </section>
    </div>

    <!-- 背景效果 -->
  <div class="background-effects" aria-hidden="true">
      <div class="bg-gradient-panel"></div>
      <div class="bg-glow"></div>
      <div class="bg-grid-pattern"></div>
    </div>
  </div>
  
</template>

<script setup>
import { ref, computed } from 'vue'
import { User, Lock } from '@element-plus/icons-vue'

// 表单状态
const account = ref('')
const password = ref('')
const showPassword = ref(false)
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
    // 通过统一的 API 封装调用管理员登录接口
    const { adminLogin } = await import('../api/auth.js')
    const resp = await adminLogin({ account: account.value.trim(), password: password.value })

    // HTTP错误（例如未启动后端）
    if (!resp.ok) {
      // 显示更友好的提示
      if (resp.status === 404) {
        error.value = '接口未找到：请确认后端已实现 /api/auth/adminManager-login 或正确配置代理域名'
      } else if (resp.status === 401) {
        error.value = '认证失败：请检查账号或密码'
      } else {
        error.value = `网络错误（${resp.status}）：请稍后重试`
      }
      return
    }

    const json = await resp.json()
    if (json.code !== 0) {
      // 字段级错误提示（API文档约定）
      if (json.details && json.details.fieldErrors) {
        const first = json.details.fieldErrors[0]
        error.value = first?.message || json.message || '参数校验失败'
      } else {
        error.value = json.message || '登录失败'
      }
      return
    }

    const { token, role, profile } = json.data || {}
    if (role !== 'admin') {
      error.value = '该账号非管理员角色，无法登录管理员控制台'
      return
    }

    // 存储令牌与角色（后续路由守卫可用）
    const authPayload = { token, role, profile }
    localStorage.setItem('auth', JSON.stringify(authPayload))

    // 跳转到管理员控制台（支持 redirect 参数）
    const params = new URLSearchParams(window.location.search)
    const redirect = params.get('redirect')
    const target = redirect || '/admin-dashboard'
    window.location.href = target
  } catch (e) {
    error.value = '无法连接服务器：请确认后端服务已启动并配置 Vite 代理'
  } finally {
    loading.value = false
  }
}

function onForgot() {
  alert('忘记密码：后续将接入邮箱验证码流程（占位）')
}
</script>

<style scoped>
.page-container {
  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  /* 移除强制最小宽度，允许背景充满视口 */
  background-color: #020408;
  color: #dbe4f3;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.content-wrapper {
  width: 100%;
  max-width: 1280px; /* 提升中心容器可用宽度，在大屏更舒展 */
  display: grid;
  /* 右侧登录卡片固定宽度，避免过窄且比例随屏幕变化导致拥挤 */
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: clamp(24px, 5vw, 64px);
  align-items: center;
  padding: clamp(16px, 3vw, 24px);
  z-index: 1;
}

.intro-panel {
  text-align: left;
  display: flex;
  flex-direction: column;
  justify-content: center;
  max-width: 60ch;
}
.system-title {
  font-size: clamp(30px, 3.8vw, 46px);
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 1px;
}
.system-subtitle {
  margin-top: 14px;
  font-size: clamp(15px, 1.9vw, 19px);
  color: #9fb3d8;
}
.features {
  margin-top: 24px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.feature-item {
  padding: 8px 14px;
  border: 1px solid rgba(60, 120, 220, 0.4);
  border-radius: 8px;
  background-color: rgba(10, 20, 40, 0.3);
  font-size: clamp(12px, 1.6vw, 14px);
}

.login-panel { width: 100%; }
.login-card {
  width: 100%;
  max-width: 420px; /* 收窄登录卡片，避免“条太长”，与右侧列宽一致 */
  margin: 0 auto;
  padding: clamp(28px, 3vw, 40px);
  border-radius: 18px;
  background: rgba(20, 28, 48, 0.6);
  border: 1px solid rgba(100, 160, 255, 0.28);
  backdrop-filter: blur(14px);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5); /* 收敛阴影避免过重 */
}

.login-title {
  font-size: clamp(22px, 2.4vw, 26px);
  font-weight: 600;
  color: #ffffff;
}
.login-subtitle {
  margin-top: 6px;
  font-size: clamp(13px, 1.7vw, 15px);
  color: #97acd0;
}

.login-form { margin-top: 24px; }

.submit-button { width: 100%; }

/* 使用 Element Plus 的按钮 loading，移除自定义 loading 样式 */

.error-alert { margin-top: 8px; }

.aux-actions { margin-top: 4px; text-align: right; }

.footer-note {
  margin-top: 24px;
  font-size: 12px;
  color: #7a8aa7;
  text-align: center;
}

.background-effects { position: fixed; inset: 0; overflow: hidden; z-index: 0; pointer-events: none; }
.bg-gradient-panel {
  position: absolute;
  inset: 0;
  /* 深蓝渐变，作为统一的全屏背景基底 */
  background: linear-gradient(180deg, rgba(10, 18, 32, 0.95) 0%, rgba(10, 18, 32, 0.88) 50%, rgba(8, 14, 24, 0.92) 100%);
}
.bg-glow {
  position: absolute;
  top: 10%;
  left: 15%;
  width: min(70vw, 900px);
  height: min(70vw, 900px);
  border-radius: 50%;
  background: radial-gradient(circle, rgba(74, 144, 226, 0.18), transparent 62%);
  filter: blur(120px);
}
.bg-grid-pattern {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.035) 1px, transparent 1px);
  background-size: 28px 28px;
  /* 去除遮罩，网格充满全屏 */
  mask-image: none;
}

/* 响应式断点调整（PC优先，窄屏基本可用性） */
@media (max-width: 1080px) { .content-wrapper { grid-template-columns: minmax(0, 1fr) 380px; } }
@media (max-width: 920px) {
  .page-container { min-width: 600px; } /* 保留基本可用性 */
  .content-wrapper { grid-template-columns: 1fr; }
  .intro-panel { margin-bottom: 8px; }
  .login-card { max-width: 520px; margin: 0 auto; }
}
@media (max-width: 600px) {
  .features { gap: 8px; }
  .feature-item { padding: 6px 10px; }
  .login-card { border-radius: 14px; box-shadow: 0 12px 36px rgba(0, 0, 0, 0.45); }
  .bg-grid-pattern { background-size: min(2.5vw, 32px) min(2.5vw, 32px); }
}
</style>