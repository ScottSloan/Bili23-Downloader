// 检查新版本
//
// 桌面版是 `util/misc/update.py` 的 `Updater`（Qt 异步 + signal_bus）。协议那一半
// 抽到了 `util/misc/update_check.py`，两端共用；这里只管什么时候问、结果怎么摆。
//
// **不轮询。** 进页面时问一次，之后只有用户点标题栏那个按钮才再问。
// 版本发布是以天计的事，没有任何理由每隔几分钟去敲一次别人的服务。

import { defineStore } from 'pinia'
import { settings as settingsApi } from '@/api'

interface UpdateState {
  /** 问过了没有。没问过时标题栏什么都不显示 */
  checked: boolean
  checking: boolean
  /** 这次没问成的原因（网络不通、服务端出错）。不是「没有新版本」 */
  error: string
  available: boolean
  /** 服务端标记的强制更新。只影响提示语气，不做拦截 */
  required: boolean
  version: string
  content: string
  updateUrl: string
  currentVersion: string
}

export const useUpdateStore = defineStore('update', {
  state: (): UpdateState => ({
    checked: false,
    checking: false,
    error: '',
    available: false,
    required: false,
    version: '',
    content: '',
    updateUrl: '',
    currentVersion: '',
  }),

  actions: {
    /**
     * 问一次
     *
     * `manual` 为 true 表示是用户点出来的 —— 那时「已是最新」也要说一声，
     * 自动那次则只在有新版本时才出声，与桌面版 `Updater.manual` 同一个语义
     */
    async check(manual = false): Promise<{ manual: boolean; available: boolean; error: string }> {
      if (this.checking) {
        return { manual, available: this.available, error: this.error }
      }

      this.checking = true

      try {
        const result = await settingsApi.checkUpdate()

        this.checked = true
        this.error = result.checked ? '' : result.error
        this.available = Boolean(result.should_update)
        this.required = Boolean(result.required)
        this.version = result.version
        this.content = result.content
        this.updateUrl = result.update_url
        this.currentVersion = result.current_version
      } catch (e) {
        this.error = e instanceof Error ? e.message : String(e)
      } finally {
        this.checking = false
      }

      return { manual, available: this.available, error: this.error }
    },
  },
})
