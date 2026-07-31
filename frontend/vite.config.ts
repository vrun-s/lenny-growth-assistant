import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import path from "node:path"

export default defineConfig({
  plugins: [react(), tailwindcss()],

  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },

  server: {
    port: 5173,
    proxy: {
      // 127.0.0.1, not "localhost" — Node resolves "localhost" to ::1 on
      // Windows, but uvicorn's default bind (127.0.0.1) is IPv4-only.
      "/api": "http://127.0.0.1:8000",
    },
  },
})