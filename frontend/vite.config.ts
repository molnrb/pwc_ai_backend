import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';
import {defineConfig, loadEnv} from 'vite';

export default defineConfig(({mode}) => {
  const env = loadEnv(mode, '.', '');
  return {
    plugins: [react(), tailwindcss()],
    define: {
      'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY),
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modify—file watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      proxy: {
        '/audit': 'http://localhost:8000',
        '/stream': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
        '/evidence': 'http://localhost:8000',
        '/health': 'http://localhost:8000',
        '/upload': 'http://localhost:8000',
        '/report': 'http://localhost:8000',
        '/reset': 'http://localhost:8000',
      },
    },
  };
});
