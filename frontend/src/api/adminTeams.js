// 管理员：队伍管理 API 封装
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
 * 列出队伍（可按赛季、状态、锁定筛选）
 * @param {{ season_id?: number, status?: string, locked?: boolean }} params
 */
export async function listTeams(params = {}) {
  const qs = new URLSearchParams()
  if (params.season_id != null) qs.set('season_id', String(params.season_id))
  if (params.status) qs.set('status', params.status)
  if (params.locked != null) qs.set('locked', String(!!params.locked))
  const resp = await fetch(`${API_URL}/admin/teams?${qs.toString()}`.replace(/\?$/, ''), {
    method: 'GET',
    headers: { ...authHeader() },
  })
  return resp
}

/** 锁定队伍 */
export async function lockTeam(teamId) {
  const resp = await fetch(`${API_URL}/admin/teams/${teamId}/lock`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
  })
  return resp
}

/** 解锁队伍 */
export async function unlockTeam(teamId) {
  const resp = await fetch(`${API_URL}/admin/teams/${teamId}/unlock`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
  })
  return resp
}

/** 删除队伍（谨慎操作，建议页面加确认） */
export async function deleteTeam(teamId) {
  const resp = await fetch(`${API_URL}/admin/teams/${teamId}/delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
  })
  return resp
}

/** 转移队长 */
export async function transferCaptain(teamId, newCaptainId) {
  const resp = await fetch(`${API_URL}/admin/teams/${teamId}/transfer-captain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify({ new_captain_id: newCaptainId }),
  })
  return resp
}

/** 移除成员 */
export async function removeMember(teamId, studentId) {
  const resp = await fetch(`${API_URL}/admin/teams/${teamId}/remove-member`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify({ student_id: studentId }),
  })
  return resp
}