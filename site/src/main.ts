import { ViteSSG } from 'vite-ssg'
import type { RouteRecordRaw } from 'vue-router'
import './style.scss'
import Root from './Root.vue'
import App from './App.vue'
import AboutPage from './AboutPage.vue'
import { BANK_PAGES, bankPagePath } from './bankPages'

const routes: RouteRecordRaw[] = [
  { path: '/', component: App },
  { path: '/about', component: AboutPage },
  ...BANK_PAGES.map((b) => ({ path: bankPagePath(b.slug), component: App, props: { bank: b.name } })),
]

export const createApp = ViteSSG(Root, { routes })
