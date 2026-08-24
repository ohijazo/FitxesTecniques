import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // El projecte viu en una unitat de xarxa (P:); el watcher natiu de Windows
    // hi peta amb ECONNRESET quan un altre procés escriu als fitxers.
    watch: { usePolling: true, interval: 300 },
    proxy: {
      '/api': {
        target: 'http://localhost:50002',
        changeOrigin: true,
      },
    },
  },
})
