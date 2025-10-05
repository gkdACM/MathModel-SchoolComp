import { API_URL } from './config'

function authHeader() {
  try {
    const raw = localStorage.getItem('auth')
    const auth = raw ? JSON.parse(raw) : null
    if (auth?.token) return { Authorization: `Bearer ${auth.token}` }
  } catch {}
  return {}
}

export async function studentLogin(payload) {
  const resp = await fetch(`${API_URL}/auth/student-login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return resp
}

export async function enrollCompetition(seasonId) {
  const resp = await fetch(`${API_URL}/student/competitions/${seasonId}/enroll`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
  })
  return resp
}

export async function createTeamForSeason(seasonId, body) {
  const resp = await fetch(`${API_URL}/student/competitions/${seasonId}/teams`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(body || {}),
  })
  return resp
}

export async function getMyTeam(seasonId) {
  const resp = await fetch(`${API_URL}/student/competitions/${seasonId}/my-team`, {
    method: 'GET',
    headers: { ...authHeader() },
  })
  return resp
}

export async function joinTeamByToken(token) {
  const resp = await fetch(`${API_URL}/student/teams/join`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify({ token }),
  })
  return resp
}

export async function generateJoinToken(teamId) {
  const resp = await fetch(`${API_URL}/student/teams/${teamId}/join-token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
  })
  return resp
}

/**
 * 上传作品（学生，双文件）
 * FormData: thesis (PDF), materials (RAR/ZIP/7Z), note? (string)
 * @param {number} teamId
 * @param {File} thesisFile
 * @param {File} materialsFile
 * @param {string=} note
 */
export async function uploadSubmission(teamId, thesisFile, materialsFile, note) {
  const fd = new FormData()
  fd.append('thesis', thesisFile)
  fd.append('materials', materialsFile)
  if (note) fd.append('note', note)
  const resp = await fetch(`${API_URL}/student/teams/${teamId}/submissions`, {
    method: 'POST',
    headers: { ...authHeader() },
    body: fd,
  })
  return resp
}

/**
 * 获取队伍提交记录（学生）
 * @param {number} teamId
 */
export async function listSubmissions(teamId) {
  const resp = await fetch(`${API_URL}/student/teams/${teamId}/submissions`, {
    method: 'GET',
    headers: { ...authHeader() },
  })
  return resp
}