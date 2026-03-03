import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  return {
    plugins: [react(), tailwindcss()],
    define: {
      'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY),
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      hmr: process.env.DISABLE_HMR !== 'true',
      port: 3000,
      proxy: {
        // Proxy API and auth routes to the bot's web server
        '/api': {
          target: 'http://localhost:10547',
          changeOrigin: true,
        },
        '/auth': {
          target: 'http://localhost:10547',
          changeOrigin: true,
        },
      },
    },
  };
});
