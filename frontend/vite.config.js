import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Enable HMR (Hot Module Replacement) - auto-reload on file changes
    hmr: {
      overlay: true, // Show error overlay
    },
    // Watch for file changes
    watch: {
      usePolling: false, // Use native file system events (faster)
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})

