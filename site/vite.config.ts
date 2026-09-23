import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  build: {
    // vite-ssg awaits every async component during prerender, so with the
    // default per-chunk CSS splitting it collects *all* component
    // stylesheets as "needed by this page" and injects each as its own
    // render-blocking <link> — more requests and more total bytes (shared
    // styles duplicated per chunk) than one bundled file. Keep it bundled.
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          if (id.includes('node_modules/vue')) return 'vue';
        },
      },
    },
  },
})
