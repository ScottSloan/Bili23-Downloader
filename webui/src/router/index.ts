import { createRouter, createWebHistory } from 'vue-router'
import ParseView from '@/views/ParseView.vue'
import DownloadView from '@/views/DownloadView.vue'
import SettingsView from '@/views/SettingsView.vue'

// 登录页不在路由里：它没有导航栏，不属于主界面外壳，由 App.vue 顶层切换。
// 放进路由的话就要再写一道守卫，与那个切换是两套互相打架的机制
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
