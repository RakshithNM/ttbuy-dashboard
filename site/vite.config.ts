import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { Features } from 'lightningcss'
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import type {} from 'vite-ssg/node'
import { BANK_PAGES, SITE_URL, bankPagePath } from './src/bankPages.ts'

const root = fileURLToPath(new URL('.', import.meta.url))

// Writes dist/sitemap.xml after the prerender. <lastmod> is the newest rate
// date in rates.json, so each daily scrape gives Google a new date to act on
// (Google ignores changefreq and priority, but uses an accurate lastmod to
// decide when to recrawl).
function writeSitemap() {
  const rates = JSON.parse(readFileSync(`${root}public/data/rates.json`, 'utf8')) as
    Record<string, Record<string, { date: string }[]>>
  let lastmod = ''
  for (const byBank of Object.values(rates))
    for (const points of Object.values(byBank))
      for (const p of points) if (p.date > lastmod) lastmod = p.date

  const paths = ['/', ...BANK_PAGES.map((b) => bankPagePath(b.slug))]
  const urls = paths
    .map((p) => `  <url>\n    <loc>${SITE_URL}${p}</loc>\n    <lastmod>${lastmod}</lastmod>\n  </url>`)
    .join('\n')
  writeFileSync(
    `${root}dist/sitemap.xml`,
    `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`,
  )
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  ssgOptions: {
    onFinished: writeSitemap,
  },
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
