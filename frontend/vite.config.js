import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// 说明：
// - 读取环境变量 `VITE_API_TARGET` 作为后端地址，默认使用 http://localhost:8080
// - 代理 `/api` 到后端，避免浏览器跨域问题
// - 保留 Vite 默认端口 5173

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.VITE_API_TARGET || 'http://192.168.1.2:8080'
  return {
    plugins: [vue()],
    server: {
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          secure: false,
          ws: true,
          // 不重写路径，后端直接实现 /api/*
          rewrite: (path) => path,
        },
      },
    },
  }
})
