import { defineStore } from 'pinia'
import { settings, type SettingChoices, type SettingItem } from '@/api'
import { ApiError } from '@/api'

/**
 * 设置页的状态
 *
 * ## 值的权威在后端
 *
 * 后端的取值校验语义是**纠正而非拒绝**：越界 clamp、认不出的值回落成默认。
 * 所以保存的响应里带的是「纠正之后的值」，必须回写进本地状态 —— 不回写的话，
 * 用户把线程数填成 99、界面上一直显示 99，实际生效的却是 10。
 *
 * ## 为什么攒一批再发
 *
 * 每次保存后端都要「读盘 → 合并 → 原子替换」一整份 config.json（那份文件是和桌面版
 * 共用的，不能全量覆写）。开关连点几下就是几次全量读写，Windows 上还可能撞上
 * 「目标文件被别人打开」而重试。攒 400ms 再发一次，连续操作只落一次盘。
 */

/** 攒多久再发。够短，用户感觉不到；够长，连续拨动开关能合成一次请求 */
const SAVE_DEBOUNCE_MS = 400

type Value = SettingItem['value']

interface SettingsState {
  items: Record<string, SettingItem>
  groups: string[]
  loaded: boolean
  loading: boolean
  saving: boolean
  /** 保存失败的说明。成功后清空 */
  error: string
  /** 改过、且要重启后端才生效的项 */
  pendingRestart: string[]
  /**
   * 结构化项的候选值（画质 / 音质 / 编码 / 字幕语言）
   *
   * 单独一个接口，但**与设置本身一起拉**。原先是「打开对话框时才拉」，理由是
   * 字幕语言有 158 条 —— 实测整个响应 7.5 KB，那个理由不成立；而代价是实打实的：
   * 卡片上的摘要要靠它把 id 翻成画质名，没拉到之前显示的是「优先 127」
   */
  choices: SettingChoices | null
}

let saveTimer: ReturnType<typeof setTimeout> | null = null

// 待发送的改动。攒在 store 之外：它是「正在飞的请求」的一部分，不是界面状态，
// 放进 state 会让它出现在 devtools 的时间线里徒增噪音
let queued: Record<string, Value> = {}

// 正在飞的那次 load。**并发的调用要等它，不能直接返回** —— 见 load() 里的说明
let loading: Promise<void> | null = null

// 候选表同理：三个优先级对话框可能几乎同时要它
let choicesPromise: Promise<void> | null = null

export const useSettingsStore = defineStore('settings', {
  state: (): SettingsState => ({
    items: {},
    groups: [],
    loaded: false,
    loading: false,
    saving: false,
    error: '',
    pendingRestart: [],
    choices: null,
  }),

  getters: {
    /** 取一项的当前值。项不存在时返回 undefined —— 调用方据此跳过整张卡片 */
    value:
      (state) =>
      (attr: string): Value | undefined =>
        state.items[attr]?.value,

    has:
      (state) =>
      (attr: string): boolean =>
        attr in state.items,

    item:
      (state) =>
      (attr: string): SettingItem | undefined =>
        state.items[attr],
  },

  actions: {
    /**
     * 读配置。已经读过就直接返回，正在读则**等那一次**
     *
     * 「正在读就直接返回」曾经是这里的写法，那是错的：并发的调用方拿到的是一个
     * 还没加载完的 store，`value(...)` 全是 undefined，然后各自静默退回默认值。
     * 解析页的列配置就这么丢过一次 —— 页面初始化时同时有两个调用方，
     * 后来的那个什么也没等到，列表一直用的是内置默认列，而且不报错
     */
    async load(force = false) {
      if (this.loaded && !force) {
        return
      }

      if (loading) {
        return loading
      }

      this.loading = true

      loading = (async () => {
        try {
          const payload = await settings.read()

          const items: Record<string, SettingItem> = {}

          for (const item of payload.items) {
            items[item.attr] = item
          }

          this.items = items
          this.groups = payload.groups
          this.loaded = true
          this.error = ''
        } catch (e) {
          this.error = e instanceof ApiError ? e.message : String(e)
        } finally {
          this.loading = false

          loading = null
        }
      })()

      return loading
    },

    /** 拉候选表。只拉一次 */
    async loadChoices() {
      if (this.choices || choicesPromise) {
        return choicesPromise ?? undefined
      }

      choicesPromise = (async () => {
        try {
          this.choices = await settings.choices()
        } catch (e) {
          this.error = e instanceof ApiError ? e.message : String(e)
        } finally {
          choicesPromise = null
        }
      })()

      return choicesPromise
    },

    /**
     * 改一项
     *
     * 先就地改本地值（界面立刻有反馈），再排队发出去。后端纠正过的值回来后会覆盖它。
     *
     * `needsRestart` 由调用方给，**不读后端下发的那个 `restart`** —— 那是桌面版的
     * 语义（见 spec.ts 里的说明），两边并不总是一致
     */
    set(attr: string, value: Value, needsRestart = false) {
      const item = this.items[attr]

      if (!item || item.value === value) {
        return
      }

      item.value = value

      if (needsRestart && !this.pendingRestart.includes(attr)) {
        this.pendingRestart.push(attr)
      }

      queued[attr] = value

      if (saveTimer !== null) {
        clearTimeout(saveTimer)
      }

      saveTimer = setTimeout(() => {
        saveTimer = null

        void this.flush()
      }, SAVE_DEBOUNCE_MS)
    },

    /** 把攒着的改动立刻发出去。离开设置页时也调一次，免得改完就走丢掉最后一批 */
    async flush() {
      if (saveTimer !== null) {
        clearTimeout(saveTimer)

        saveTimer = null
      }

      const values = queued

      queued = {}

      if (!Object.keys(values).length) {
        return
      }

      this.saving = true

      try {
        const result = await settings.write(values)

        // 回写纠正后的值。**这一步不能省**，理由见文件头
        for (const [attr, corrected] of Object.entries(result.values ?? {})) {
          const item = this.items[attr]

          if (item) {
            item.value = corrected as Value
          }
        }

        this.error = ''
      } catch (e) {
        this.error = e instanceof ApiError ? e.message : String(e)

        // 保存失败时本地值已经是新的了，与后端不一致。重新拉一遍把界面拨回真实状态 ——
        // 留着一个「看起来改了其实没改」的界面比报个错更糟
        await this.load(true)
      } finally {
        this.saving = false
      }
    },
  },
})
