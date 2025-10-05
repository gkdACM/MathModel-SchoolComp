// 管理员公告管理 API 封装
import { API_URL } from './config'

function authHeader() {
  try {
    const raw = localStorage.getItem('auth')
    const auth = raw ? JSON.parse(raw) : null
    if (auth?.token) return { Authorization: `Bearer ${auth.token}`, 'Content-Type': 'application/json' }
  } catch {}
  return { 'Content-Type': 'application/json' }
}

// 分页查询公告
export async function listAdminAnnouncements(page = 1, pageSize = 20) {
  const qs = new URLSearchParams()
  qs.set('page', String(page))
  qs.set('page_size', String(pageSize))
  const resp = await fetch(`${API_URL}/admin/announcements?${qs.toString()}`, {
    method: 'GET',
    headers: { ...authHeader() },
  })
  return resp
}

// 创建公告
export async function createAdminAnnouncement(payload) {
  const resp = await fetch(`${API_URL}/admin/announcements`, {
    method: 'POST',
    headers: { ...authHeader() },
    body: JSON.stringify(payload),
  })
  return resp
}

// 更新公告
export async function updateAdminAnnouncement(id, payload) {
  const resp = await fetch(`${API_URL}/admin/announcements/${id}`, {
    method: 'POST',
    headers: { ...authHeader() },
    body: JSON.stringify(payload),
  })
  return resp
}

// 删除公告
export async function deleteAdminAnnouncement(id) {
  const resp = await fetch(`${API_URL}/admin/announcements/${id}/delete`, {
    method: 'POST',
    headers: { ...authHeader() },
  })
  return resp
}