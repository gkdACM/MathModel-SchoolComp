// 竞赛管理相关 API 封装
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
 * 创建竞赛
 * Body: { name: string, start_time: string(ISO), end_time: string(ISO), signup_start?, signup_end?, review_start?, review_end?, allow_signup?: boolean }
 */
export async function createCompetition(body) {
  const resp = await fetch(`${API_URL}/admin/competitions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(body),
  })
  return resp
}

/**
 * 上传竞赛题目 ZIP（覆盖保存）
 * @param {number} seasonId
 * @param {File} file ZIP文件
 */
export async function uploadCompetitionZip(seasonId, file) {
  const form = new FormData()
  form.append('file', file)
  const resp = await fetch(`${API_URL}/admin/competitions/${seasonId}/problems/upload`, {
    method: 'POST',
    headers: { ...authHeader() },
    body: form,
  })
  return resp
}

/**
 * 列出所有竞赛（管理员）
 * 返回：标准响应对象 { code, message, data: [ {id, name, start_time, end_time, status} ] }
 */
export async function listCompetitions() {
  const resp = await fetch(`${API_URL}/admin/competitions`, {
    method: 'GET',
    headers: { ...authHeader() },
  })
  return resp
}

/**
 * 切换报名开关
 * @param {number} seasonId
 * @param {boolean} allow
 */
export async function toggleSignup(seasonId, allow) {
  const resp = await fetch(`${API_URL}/admin/competitions/${seasonId}/signup-toggle`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify({ allow_signup: !!allow }),
  })
  return resp
}

/**
 * 导出当前赛季成绩表（CSV）
 * @param {number} seasonId
 * @returns {Promise<Response>} fetch 响应对象
 */
export async function exportScores(seasonId) {
  const resp = await fetch(`${API_URL}/admin/competitions/${seasonId}/scores/export`, {
    method: 'GET',
    headers: { ...authHeader() },
  })
  return resp
}

/**
 * 获取教师对指定赛季的评审进度统计
 * @param {number} seasonId
 * @returns {Promise<Response>} fetch 响应对象
 */
export async function reviewProgress(seasonId) {
  const resp = await fetch(`${API_URL}/admin/competitions/${seasonId}/reviews/progress`, {
    method: 'GET',
    headers: { ...authHeader() },
  })
  return resp
}

/**
 * 上传历年优秀作品文件（zip/pdf），可附带摘要/评分与下载许可
 * @param {number} seasonId 赛季ID
 * @param {File} file 文件（zip/pdf）
 * @param {{ summary?: string, score?: number, allow_download?: boolean, team_id?: number, submission_id?: number }} meta
 */
export async function uploadExcellentWork(seasonId, file, meta = {}) {
  const form = new FormData()
  form.append('file', file)
  if (meta.summary != null) form.append('summary', meta.summary)
  if (meta.score != null) form.append('score', String(meta.score))
  if (meta.allow_download != null) form.append('allow_download', String(!!meta.allow_download))
  if (meta.team_id != null) form.append('team_id', String(meta.team_id))
  if (meta.submission_id != null) form.append('submission_id', String(meta.submission_id))
  const resp = await fetch(`${API_URL}/admin/competitions/${seasonId}/excellent/upload`, {
    method: 'POST',
    headers: { ...authHeader() },
    body: form,
  })
  return resp
}