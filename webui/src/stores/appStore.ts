import { defineStore } from 'pinia'
import { login, settings, system } from '@/api'
import { setLocale } from '@/i18n'

interface AppState {
  version: string
  /** B 站账号是否已登录。**不是** WebUI 自身的登录态，那个在 authStore 里 */
  loggedIn: boolean
  uname: string
  uid: string
  faceUrl: string
  /** 后端是否可达 */
  ready: boolean
}

/**
 * 全局应用状态：版本、B 站账号、界面语言
 *
 * 界面语言从共用的 config.json 读回来（D12：共用的是「用户选了哪种语言」这个设置，
 * 不是翻译表本身）。主题不走这条链路，各存各的（D14）。
 */
export const useAppStore = defineStore('app', {
  state: (): AppState => ({
    version: '',
    loggedIn: false,
    uname: '',
    uid: '',
    faceUrl: '',
    ready: false,
  }),

  actions: {
    async fetchStatus() {
      try {
        const status = await system.status()

        this.version = status.version || ''
        this.ready = true
      } catch {
        // 后端没起来不该拦住界面渲染
        this.ready = false

        return
      }

      // 语言与 B 站账号信息分两个接口：/api/status 只报服务自身的状态，
      // 账号那部分在 /api/login/status —— 两者的刷新时机也不同
      await this.fetchAccount()
      await this.fetchLanguage()
    },

    /** 不传 refresh 时只读配置里的状态，不打 B 站接口 */
    async fetchAccount(refresh = false) {
      try {
        const info = await login.status(refresh)

        this.loggedIn = Boolean(info.logged_in)
        this.uname = info.uname || ''
        this.uid = String(info.uid ?? '')
        this.faceUrl = info.face || ''
      } catch {
        this.loggedIn = false
      }
    },

    async fetchLanguage() {
      try {
        const payload = await settings.read()

        const item = payload.items.find((entry) => entry.attr === 'language')

        // 取值是桌面版配置里那套（'Auto' / 'zh_CN' / ...），setLocale 认得
        setLocale(typeof item?.value === 'string' ? item.value : null)
      } catch {
        // 读不到就保持按浏览器语言显示，不影响使用
      }
    },
  },
})
