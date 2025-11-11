# syntax=docker/dockerfile:1
FROM node:20-alpine AS build
WORKDIR /app

# Install deps
COPY crm-frontend/package*.json /app/
RUN npm ci

# Build with base path /admin/ for production
COPY crm-frontend /app
# Устанавливаем базовый путь /admin/ для production сборки
ARG VITE_BASE_PATH=/admin/
ENV VITE_BASE_PATH=$VITE_BASE_PATH
RUN npm run build

# --- Runtime image ---
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY crm-frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=5 CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1

