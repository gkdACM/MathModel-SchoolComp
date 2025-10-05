// 管理员登录 API 封装
// 说明：统一使用 API_URL 作为基础路径，确保后端域名集中配置
import { API_URL } from './config'

/**
 * 管理员登录
 * @param {{account: string, password: string}} payload
 * @returns {Promise<any>} 后端统一响应
 */
export async function adminLogin(payload) {
  const resp = await fetch(`${API_URL}/auth/adminManager-login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return resp
}

/**
 * 教师登录
 * @param {{account: string, password: string}} payload
 * @returns {Promise<Response>} 后端统一响应
 */
export async function teacherLogin(payload) {
  const resp = await fetch(`${API_URL}/auth/teacher-login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return resp
}