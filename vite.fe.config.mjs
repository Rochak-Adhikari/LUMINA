import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Build config for the parallel new frontend (frontend.html entry).
// Kept separate from vite.config.js so the live app (index.html) is untouched.
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: 'dist-fe',
    rollupOptions: { input: 'frontend.html' },
  },
})
