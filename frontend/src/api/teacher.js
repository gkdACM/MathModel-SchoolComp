import { API_URL } from './config'

function authHeader() {
  try {
    const raw = localStorage.getItem('auth')
    const auth = raw ? JSON.parse(raw) : null
    if (auth?.token) return { Authorization: `Bearer ${auth.token}` }
  } catch {}
  return {}
}

export async function listCompetitions() {
  const resp = await fetch(`${API_URL}/teacher/competitions`, {
    method: 'GET',
    headers: { ...authHeader() },
  })
  return resp
}

export async function listSubmissions(seasonId) {
  const resp = await fetch(`${API_URL}/teacher/competitions/${seasonId}/submissions`, {
    method: 'GET',
    headers: { ...authHeader() },
  })
  return resp
}

export async function previewPdf(submissionId, fileId) {
  // 直接返回URL以供 <iframe> 使用，附带token查询参数
  let token = ''
  try {
    const raw = localStorage.getItem('auth')
    const auth = raw ? JSON.parse(raw) : null
    token = auth?.token || ''
  } catch {}
  const url = `${API_URL}/teacher/submissions/${submissionId}/files/${fileId}/pdf`
  return token ? `${url}?token=${encodeURIComponent(token)}` : url
}

export async function submitScore(submissionId, payload) {
  const resp = await fetch(`${API_URL}/teacher/submissions/${submissionId}/score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(payload),
  })
  return resp
}