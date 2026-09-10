import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './styles/theme.css'
import App from './App.vue'
import router from './router'
import { preloadLocale } from './i18n'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// 只有源语言（英文）打进主包，其余按需加载 —— 挂载之前先把当前这门等到，
// 否则中文用户会先看到一瞬间的英文界面。加载失败不阻塞挂载（那时界面是英文）
void preloadLocale().finally(() => app.mount('#app'))
