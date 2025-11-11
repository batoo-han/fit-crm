import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  // Базовый путь для production (админ-панель доступна на /admin/)
  // Для разработки оставляем '/' (можно переопределить через переменную окружения)
  base: process.env.VITE_BASE_PATH || '/',
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8009',
        changeOrigin: true,
      },
    },
  },
  build: {
    // Убеждаемся, что пути к ресурсам правильные
    assetsDir: 'assets',
    outDir: 'dist',
  },
})

