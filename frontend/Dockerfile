# 航海集市前端镜像：多阶段构建
#   第一阶段（施工队）：用 Node.js 把 Vue 代码打包成普通网页文件
#   第二阶段（成品）：只把打包结果放进 Nginx，Node.js 和 node_modules 不进最终镜像

# ---------- 第一阶段：打包 ----------
FROM node:24-slim AS build

# 国内服务器访问 npm 官方很慢，用腾讯云的 npm 镜像站（换别家云时改这个参数即可）
ARG NPM_REGISTRY=https://mirrors.cloud.tencent.com/npm/

WORKDIR /src

# 先只复制依赖清单并安装：依赖没变时这一层直接用缓存
COPY package.json package-lock.json ./
RUN npm ci --registry=${NPM_REGISTRY} --no-audit --no-fund

# 再复制源代码并打包，结果在 /src/dist
COPY . .
RUN npm run build

# ---------- 第二阶段：Nginx 提供网页 ----------
FROM nginx:stable-alpine

# 用我们的配置替换 Nginx 默认配置
COPY nginx.conf /etc/nginx/conf.d/default.conf
# 只拿第一阶段的打包结果
COPY --from=build /src/dist /usr/share/nginx/html

EXPOSE 80
