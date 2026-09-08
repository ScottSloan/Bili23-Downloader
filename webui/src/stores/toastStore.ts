// 顶部气泡提示
//
// 桌面版所有的即时反馈都走 `signal_bus.toast.show` → `InfoBar`（见
// `gui/interface/main_window.py` 的 `show_toast_notification`）：顶部居中、3 秒后自己消失。
// Web 端此前是在页面里塞一行小字，出现在哪、什么时候消失全凭各页自己写，
// 用户很容易根本没注意到。
//
// 这里补上同一套东西。分类沿用桌面版的 `ToastNotificationCategory`
// （info / success / warning / error），颜色与图标也照它那份配。
//
// **长消息**对应桌面版的 `show_toast_notification_long_message`：右下角、可关闭、
// 5 秒、内容竖排。用在那种「说明为什么失败」的长文本上。

import { defineStore } from 'pinia'

export type ToastCategory = 'info' | 'success' | 'warning' | 'error'

export interface Toast {
  id: number
  category: ToastCategory
  title: string
  content: string
  /** 顶部居中（短提示）还是右下角（长消息） */
  position: 'top' | 'bottom-right'
  closable: boolean
  /** 毫秒。0 表示不自动消失 */
  duration: number
}

interface ToastState {
  toasts: Toast[]
}

let nextId = 1

export const useToastStore = defineStore('toast', {
  state: (): ToastState => ({
    toasts: [],
  }),

  actions: {
    /**
     * 弹一条提示
     *
     * 同一条消息短时间内重复弹（比如轮询里反复失败）只会刷新最后那条的计时，
     * 不会在屏幕上堆成一列 —— 桌面版不会遇到这个，Web 端的自动刷新会
     */
    show(
      category: ToastCategory,
      title: string,
      content = '',
      options: { position?: Toast['position']; closable?: boolean; duration?: number } = {},
    ): number {
      const existing = this.toasts.find(
        (toast) =>
          toast.category === category && toast.title === title && toast.content === content,
      )

      if (existing) {
        // 重新计时：把它挪到队尾，宿主组件会据此重设定时器
        this.toasts = [...this.toasts.filter((toast) => toast.id !== existing.id), existing]

        return existing.id
      }

      const long = options.position === 'bottom-right'

      const toast: Toast = {
        id: nextId++,
        category,
        title,
        content,
        position: options.position ?? 'top',
        // 与桌面版一致：短提示不可关闭（3 秒就没了），长消息可以关
        closable: options.closable ?? long,
        duration: options.duration ?? (long ? 5000 : 3000),
      }

      this.toasts.push(toast)

      return toast.id
    },

    info: (title: string, content = '') => useToastStore().show('info', title, content),
    success: (title: string, content = '') => useToastStore().show('success', title, content),
    warning: (title: string, content = '') => useToastStore().show('warning', title, content),
    error: (title: string, content = '') => useToastStore().show('error', title, content),

    /** 长消息：右下角、可关闭、5 秒（桌面版 show_toast_notification_long_message） */
    longMessage(category: ToastCategory, title: string, content: string) {
      return this.show(category, title, content, { position: 'bottom-right' })
    },

    dismiss(id: number) {
      this.toasts = this.toasts.filter((toast) => toast.id !== id)
    },

    clear() {
      this.toasts = []
    },
  },
})
