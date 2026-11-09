import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import Components from 'unplugin-vue-components/vite'
import { defineConfig } from 'vite'

const BACKEND = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
    // Element Plus（只用于管理后台）按需引入：el-table 等不用手动 import
    // dirs: [] 关闭对 src/components 的自动注册，网站页面里的组件一律显式 import，便于阅读
    AutoImport({ resolvers: [ElementPlusResolver()] }),
    Components({ resolvers: [ElementPlusResolver()], dirs: [] }),
  ],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    // 开发时把接口和图片请求转发给后端，前端代码里直接写 /api/... 即可，没有跨域问题
    proxy: {
      '/api': BACKEND,
      '/uploads': BACKEND,
    },
  },
})
