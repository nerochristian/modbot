import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:10547',
      '/auth': 'http://localhost:10547',
      '/health': 'http://localhost:10547',
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  }
})
