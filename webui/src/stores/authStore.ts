import { defineStore } from 'pinia'
import { auth, ApiError } from '@/api'
import { t } from '@/i18n'

/**
 * WebUI 自身的登录态（D6 的单用户口令）
 *
 * **与 B 站账号的登录是两回事**：这里管的是「能不能进这个网页」，
 * B 站账号那套在 `bilibiliStore` 里。两者都叫「登录」，但一个是本地服务的门禁，
 * 一个是去 B 站取数据的凭证 —— 界面上要分开说，不然用户会以为退出登录会把 B 站也退掉。
 */
interface AuthState {
  authenticated: boolean
  username: string
  /** 首次查会话之前为真。这段时间既不该显示登录页也不该显示主界面，否则会闪一下 */
  checking: boolean
  error: string
  submitting: boolean
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    authenticated: false,
    username: '',
    checking: true,
    error: '',
    submitting: false,
  }),

  actions: {
    /** 首屏调一次。`/api/auth/session` 是豁免鉴权的，未登录时返回 authenticated: false 而不是 401 */
    async check() {
      this.checking = true

      try {
        const info = await auth.session()

        this.authenticated = Boolean(info.authenticated)
        this.username = info.username || ''
      } catch {
        // 后端没起来。这时既不能说「已登录」也不该跳登录页去让用户白输一遍密码，
        // 保持未登录，由 LoginView 上的错误提示告诉他后端不可达
        this.authenticated = false
      } finally {
        this.checking = false
      }
    },

    async login(username: string, password: string): Promise<boolean> {
      this.submitting = true
      this.error = ''

      try {
        const info = await auth.login(username, password)

        this.authenticated = Boolean(info.authenticated)
        this.username = info.username || ''

        return this.authenticated
      } catch (error) {
        // 登录失败次数过多时后端回 429，那句话比「用户名或密码错误」有用得多，原样显示
        this.error = error instanceof ApiError && error.message ? error.message : t('auth.failed')

        return false
      } finally {
        this.submitting = false
      }
    },

    async logout() {
      try {
        await auth.logout()
      } catch {
        // 后端没响应也要把本地状态清掉：界面还停在已登录更糟
      }

      this.authenticated = false
      this.username = ''
    },

    /** 任何一次请求收到 401 都会走到这里（见 client.ts 的 setUnauthorizedHandler） */
    onSessionExpired() {
      if (!this.authenticated) {
        return
      }

      this.authenticated = false
      this.username = ''
      this.error = t('auth.expired')
    },
  },
})
