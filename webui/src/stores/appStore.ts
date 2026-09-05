import { defineStore } from 'pinia'
import { api } from '@/api/client'
import { setLocale } from '@/i18n'
import type { StatusPayload } from '@/api/types'

interface AppState {
  version: string
  loggedIn: boolean
  uname: string
  uid: string
  faceUrl: string
  /** 后端是否可达。首屏拉不到状态时界面照常渲染，只是登录区显示未登录 */
  ready: boolean
}

/**
 * 全局应用状态：版本、登录态、界面语言
 *
 * 只有语言是从桌面版配置读回来的（两边共用 config.json）。主题不走这条链路 ——
 * 主题各存各的，见 docs/webui/DECISIONS.md 的 D14
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
    _apply(payload: StatusPayload) {
      this.version = payload.version || ''
      this.loggedIn = Boolean(payload.logged_in)
      this.uname = payload.uname || ''
      this.uid = String(payload.uid ?? '')
      this.faceUrl = payload.face_url || ''
      this.ready = true

      // 界面语言跟随桌面版设置
      setLocale(payload.language)
    },

    async fetchStatus() {
      try {
        this._apply(await api.getStatus())
      } catch {
        // 后端没起来不该拦住界面渲染，保持未登录态即可
        this.ready = false
      }
    },
  },
})
