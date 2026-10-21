import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { Features } from 'lightningcss'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  css: {
    lightningcss: {
      // Without this, Lightning CSS's minify step down-levels light-dark()
      // into --lightningcss-light/-dark custom properties — including a
      // declaration with an intentionally empty value (e.g.
      // `--lightningcss-light: ;`), which is valid CSS but which jsdom's
      // bundled CSS parser (used during vite-ssg's SSR prerender) can't
      // parse, logging "Could not parse CSS stylesheet" at build time.
      // build.cssTarget doesn't fix this even set to versions that support
      // light-dark() natively (verified empirically) — this exclude flag is
      // the documented way to force-skip one specific down-level regardless
      // of targets, and — unlike css.lightningcss.targets — Vite's minify
      // step doesn't override it (it only overrides `targets`; verified by
      // reading vite/dist/node/chunks/node.js). This app already assumes
      // modern evergreen browsers (View Transitions API, color-mix()), so
      // native light-dark() (Chrome 123+, Safari 17.5+, Firefox 120+) is fine.
      exclude: Features.LightDark,
    },
  },
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
          // The data JSON is imported (not fetched) so the prerender includes
          // it. Its own chunk keeps the app chunk's hash stable when the
          // daily scrape changes only the data.
          if (id.includes('/public/data/')) return 'data';
        },
        // A hashed data file name would end up inside the app chunk's import
        // and change its hash every day anyway. A fixed name breaks that
        // chain; _headers makes browsers revalidate it on every visit.
        chunkFileNames: (chunk) =>
          chunk.name === 'data' ? 'app-data/data.js' : 'assets/[name]-[hash].js',
      },
    },
  },
})
