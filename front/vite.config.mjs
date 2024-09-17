import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import ViteFonts from 'unplugin-fonts/vite'
import { fileURLToPath, URL } from 'node:url'


// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vuetify({ 
      autoImport: true,
      styles: { configFile: 'src/styles/settings.scss' }
    }),
    ViteFonts({
      google: {
        families: [{
          name: 'Roboto',
          styles: 'wght@100;300;400;500;700;900',
        }],
      },
    }),
  ],
  define: { 'process.env': {} },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@components': fileURLToPath(new URL('./src/components', import.meta.url)),
      '@charts': fileURLToPath(new URL('./src/components/charts', import.meta.url)),
      '@trading': fileURLToPath(new URL('./src/components/trading', import.meta.url)),
      '@session': fileURLToPath(new URL('./src/components/session', import.meta.url)),
      '@assets': fileURLToPath(new URL('./src/assets', import.meta.url)), // New line added

    },
    extensions: [
      '.js',
      '.json',
      '.jsx',
      '.mjs',
      '.ts',
      '.tsx',
      '.vue',
    ],
  },
  server: {
    port: 3000,
    hmr: {
      host: 'localhost',
      protocol: 'ws'
    },
    cors: true  // Enable CORS for development server
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@import "@/styles/variables.scss";`
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            return 'vendor';
          }
        }
      }
    },
    chunkSizeWarningLimit: 1000,  // Increase the chunk size warning limit
  },
  optimizeDeps: {
    include: ['vue', 'vuetify']
  }
})