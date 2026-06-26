# 前端 Dockerfile — Vue 3 + Nginx
FROM node:18-alpine AS build

WORKDIR /app

# 安装依赖（利用 Docker 层缓存）
COPY package*.json ./
RUN npm ci

# 复制源码 + 环境变量（.env.production 设定 VITE_API_BASE=/api，Nginx 代理到后端）
COPY . .
RUN npm run build

# 生产镜像
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
