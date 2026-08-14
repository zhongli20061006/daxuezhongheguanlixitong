import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: true,        // 允许局域网访问前端
    port: 5175,
    proxy: {
      // WebSocket 走同源：dev 由 vite 转发到后端 8000（生产由 nginx 转发）
      '/ws': { target: 'ws://localhost:8000', ws: true, changeOrigin: true }
    }
  }
})
