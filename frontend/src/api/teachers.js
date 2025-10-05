// 教师相关 API 封装
import { API_URL } from './config'

/**
 * 批量生成教师账号
 * Body: { names: string[] }
 * 响应：{ code: 0, data: { rows: [{ name, account, tempPassword, status? }] } }
 */
export async function generateTeachers(body) {
  const resp = await fetch(`${API_URL}/admin/teachers/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      // 可选：后续接入 token
      ...(function() {
        try {
          const raw = localStorage.getItem('auth')
          const auth = raw ? JSON.parse(raw) : null
          if (auth?.token) return { Authorization: `Bearer ${auth.token}` }
        } catch {}
        return {}
      })(),
    },
    body: JSON.stringify(body),
  })
  return resp
}

/**
 * 初始化教师密码为默认值
 * Body: { accounts?: string[], all?: boolean }
 * 响应：{ code: 0, data: { rows: [{account,name,status}], updated, defaultPassword } }
 */
export async function initTeacherPasswords(body) {
  const resp = await fetch(`${API_URL}/admin/teachers/password/init`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(function() {
        try {
          const raw = localStorage.getItem('auth')
          const auth = raw ? JSON.parse(raw) : null
          if (auth?.token) return { Authorization: `Bearer ${auth.token}` }
        } catch {}
        return {}
      })(),
    },
    body: JSON.stringify(body || {}),
  })
  return resp
}

/**
 * 导出教师密码CSV（默认密码才会显示）
 */
export async function exportTeacherPasswords() {
  const resp = await fetch(`${API_URL}/admin/teachers/password/export`, {
    method: 'GET',
    headers: {
      ...(function() {
        try {
          const raw = localStorage.getItem('auth')
          const auth = raw ? JSON.parse(raw) : null
          if (auth?.token) return { Authorization: `Bearer ${auth.token}` }
        } catch {}
        return {}
      })(),
    },
  })
  return resp
}