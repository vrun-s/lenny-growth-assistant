import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // 127.0.0.1, not "localhost" — Node resolves "localhost" to ::1 on
      // Windows, but uvicorn's default bind (127.0.0.1) is IPv4-only, so
      // "localhost" here silently ECONNREFUSEDs while curl to "localhost"
      // works fine (curl tries both families).
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
