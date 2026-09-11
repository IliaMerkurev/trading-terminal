import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
  root: 'frontend', plugins: [react()],
  server: {
    host: '127.0.0.1', port: 1420, strictPort: true,
    fs: { strict: true, deny: ['**/.private/**', '**/.local-data/**', '**/.local-tools/**', '**/.env*', '**/*.pem', '**/*.key'] },
  },
  build: { outDir: '../dist', emptyOutDir: true },
});
