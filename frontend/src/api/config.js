// 统一的后端域名配置，读取 Vite 环境变量或回退到代理前缀
// 使用方式：import { API_BASE_URL } from './config'
// 在生产环境中建议显式设置 VITE_API_TARGET，例如 https://api.example.com

// 为方便本地管理，硬编码后端基础地址到 8080
// 注意：使用绝对路径将绕过 Vite 代理，需确保后端允许 CORS
// 开发环境默认指向本机后端端口 8080
export const API_URL = (import.meta.env?.VITE_API_URL) || 'http://192.168.1.2:8080/api'
