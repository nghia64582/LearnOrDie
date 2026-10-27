import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    port: 5173,
    host: 'localhost'
  },
  optimizeDeps: {
    include: ['@jscad/modeling', '@jscad/regl-renderer', '@jscad/stl-serializer']
  }
})
