import { createRouter, createWebHistory } from 'vue-router'
import ParseView from '@/views/ParseView.vue'
import DownloadView from '@/views/DownloadView.vue'
import SettingsView from '@/views/SettingsView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/parse',
    },
    {
      path: '/parse',
      name: 'parse',
      component: ParseView,
    },
    {
      path: '/download',
      name: 'download',
      component: DownloadView,
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView,
    },
  ],
})

export default router
