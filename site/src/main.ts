import { ViteSSG } from 'vite-ssg'
import type { RouteRecordRaw } from 'vue-router'
import './style.scss'
import Root from './Root.vue'
import App from './App.vue'
import AboutPage from './AboutPage.vue'
import NotFoundPage from './NotFoundPage.vue'
import { BANK_PAGES, bankPagePath } from './bankPages'

const routes: RouteRecordRaw[] = [
  { path: '/', component: App },
  { path: '/about', component: AboutPage },
  ...BANK_PAGES.map((b) => ({ path: bankPagePath(b.slug), component: App, props: { bank: b.name } })),
  // /404 is prerendered to 404.html (vite-ssg skips the catch-all). Cloudflare
  // serves that file for unknown paths, and the catch-all hydrates it there.
  { path: '/404', component: NotFoundPage },
  { path: '/:pathMatch(.*)*', component: NotFoundPage },
]

export const createApp = ViteSSG(Root, { routes })
