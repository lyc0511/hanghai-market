# 航海集市 · 前端

Vue 3 + Vite 8 + Vue Router 5 + Pinia 4 + Axios。

- **前台网站**：Tailwind CSS 4 + shadcn-vue（reka-ui）+ motion-v 动效（「港口公告牌」视觉主题，设计规范见 `src/styles/main.css`）
- **管理后台（`/admin`）**：Element Plus（样式变量见 `src/styles/theme.css`）

```powershell
npm install
npm run dev      # http://localhost:5173，开发代理将 /api 与 /uploads 转发至后端 8000 端口
npm run build    # 打包到 dist/
```

项目整体架构、接口清单与后端启动说明见上一级 [README.md](../README.md)。
