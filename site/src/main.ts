import { ViteSSG } from 'vite-ssg/single-page'
import './style.scss'
import App from './App.vue'

export const createApp = ViteSSG(App)
