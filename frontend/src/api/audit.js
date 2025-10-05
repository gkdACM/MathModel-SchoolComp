// 审计日志相关 API 封装
import { API_URL } from './config'

function authHeader() {
  try {
    const raw = localStorage.getItem('auth')
    const auth = raw ? JSON.parse(raw) : null
    if (auth?.token) return { Authorization: `Bearer ${auth.token}` }
  } catch {}
  return {}
}

/**
 * 分页查询审计日志
 * @param {{ actor_type?: string, actor_id?: number, action?: string, object_type?: string, object_id?: number, start_time?: string, end_time?: string, page?: number, page_size?: number }} params
 */
export async function listAuditLogs(params = {}) {
  const qs = new URLSearchParams()
  if (params.actor_type) qs.set('actor_type', params.actor_type)
  if (params.actor_id != null) qs.set('actor_id', String(params.actor_id))
  if (params.action) qs.set('action', params.action)
  if (params.object_type) qs.set('object_type', params.object_type)
  if (params.object_id != null) qs.set('object_id', String(params.object_id))
  if (params.start_time) qs.set('start_time', params.start_time)
  if (params.end_time) qs.set('end_time', params.end_time)
  if (params.page != null) qs.set('page', String(params.page))
  if (params.page_size != null) qs.set('page_size', String(params.page_size))
  const url = `${API_URL}/admin/audit/logs` + (qs.toString() ? `?${qs.toString()}` : '')
  const resp = await fetch(url, { method: 'GET', headers: { ...authHeader() } })
  return resp
}

/**
 * 导出审计日志为 CSV
 * 同 params 过滤条件
 */
export async function exportAuditLogs(params = {}) {
  const qs = new URLSearchParams()
  if (params.actor_type) qs.set('actor_type', params.actor_type)
  if (params.actor_id != null) qs.set('actor_id', String(params.actor_id))
  if (params.action) qs.set('action', params.action)
  if (params.object_type) qs.set('object_type', params.object_type)
  if (params.object_id != null) qs.set('object_id', String(params.object_id))
  if (params.start_time) qs.set('start_time', params.start_time)
  if (params.end_time) qs.set('end_time', params.end_time)
  const url = `${API_URL}/admin/audit/logs/export` + (qs.toString() ? `?${qs.toString()}` : '')
  const resp = await fetch(url, { method: 'GET', headers: { ...authHeader() } })
  return resp
}