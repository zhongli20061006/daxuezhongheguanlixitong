import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: true,        // 允许局域网访问前端
    port: 5175,
    proxy: {}
  }
})
