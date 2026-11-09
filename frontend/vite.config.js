import { fileURLToPath, URL } from 'node:url'

import { VantResolver } from '@vant/auto-import-resolver'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import Components from 'unplugin-vue-components/vite'
import { defineConfig } from 'vite'

const BACKEND = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [
    vue(),
    // 用到哪个组件才打包哪个（van-button、el-table 等不用手动 import）
    AutoImport({ resolvers: [VantResolver(), ElementPlusResolver()] }),
    Components({ resolvers: [VantResolver(), ElementPlusResolver()] }),
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
