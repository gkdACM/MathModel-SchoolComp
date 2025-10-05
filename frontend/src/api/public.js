// 公共接口封装：优秀作品与开放竞赛
import { API_URL } from './config'

export async function listExcellentWorks(params = {}) {
  const qs = new URLSearchParams()
  if (params.season_id) qs.set('season_id', String(params.season_id))
  if (params.limit) qs.set('limit', String(params.limit))
  const resp = await fetch(`${API_URL}/public/excellent-works?${qs.toString()}`)
  return resp
}

export async function listOpenCompetitions() {
  const resp = await fetch(`${API_URL}/public/open-competitions`)
  return resp
}

// 公告分页查询：默认每页3条
export async function listAnnouncements(page = 1, pageSize = 3) {
  const qs = new URLSearchParams()
  qs.set('page', String(page))
  qs.set('page_size', String(pageSize))
  const resp = await fetch(`${API_URL}/public/announcements?${qs.toString()}`)
  return resp
}