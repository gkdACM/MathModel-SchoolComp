import { API_URL } from './config'

/**
 * 学生注册
 * Body: { studentId, name, college, class, email, password }
 */
export async function studentRegister(body) {
  // 前端按文档使用 "class" 字段名，后端为 class_name；此处做一次映射
  const payload = { ...body }
  if (payload && payload.class) {
    payload.class_name = payload.class
    delete payload.class
  }
  const resp = await fetch(`${API_URL}/auth/student/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return resp
}