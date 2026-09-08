<script setup lang="ts">
/**
 * 气泡提示的宿主：管住位置、堆叠与自动消失
 *
 * 对应 qfluentwidgets 的 `InfoBarManager`：顶部居中距边 24、条与条之间 16，
 * 入场是 200ms OutQuad 从上方 16px 滑下来，退场是 200ms 淡出。
 * 长消息那一路对应 `BottomRightInfoBarManager`。
 *
 * 计时放在这里而不是 store：store 里挂一堆 setTimeout，热更新或切页时清不干净。
 * 这里跟着组件生命周期走，卸载时一并清掉。
 */
import { onBeforeUnmount, watch } from 'vue'
import { storeToRefs } from 'pinia'
import fluentInfoBar from './FluentInfoBar.vue'
import { useToastStore } from '@/stores/toastStore'

const store = useToastStore()
const { toasts } = storeToRefs(store)

const timers = new Map<number, ReturnType<typeof setTimeout>>()

function arm(id: number, duration: number) {
  const existing = timers.get(id)

  if (existing) {
    clearTimeout(existing)
  }

  if (!duration) {
    return
  }

  timers.set(
    id,
    setTimeout(() => {
      timers.delete(id)

      store.dismiss(id)
    }, duration),
  )
}

// 每条出现（或被同一条消息刷新）时重设计时器；消失的把定时器收掉，
// 否则它会在几秒后去 dismiss 一个已经不存在的 id
watch(
  toasts,
  (list) => {
    const alive = new Set(list.map((toast) => toast.id))

    for (const [id, timer] of timers) {
      if (!alive.has(id)) {
        clearTimeout(timer)

        timers.delete(id)
      }
    }

    for (const toast of list) {
      arm(toast.id, toast.duration)
    }
  },
  { deep: true, immediate: true },
)

onBeforeUnmount(() => {
  for (const timer of timers.values()) {
    clearTimeout(timer)
  }

  timers.clear()
})
</script>

<template>
  <!-- 挂到 body 上：页面里任何一层的 overflow: hidden 都不该把提示裁掉 -->
  <teleport to="body">
    <div class="info-bar-host is-top">
      <transition-group name="drop">
        <fluentInfoBar
          v-for="toast in toasts.filter((item) => item.position === 'top')"
          :key="toast.id"
          :category="toast.category"
          :title="toast.title"
          :content="toast.content"
          :closable="toast.closable"
          @close="store.dismiss(toast.id)"
        />
      </transition-group>
    </div>

    <div class="info-bar-host is-bottom-right">
      <transition-group name="drop">
        <fluentInfoBar
          v-for="toast in toasts.filter((item) => item.position === 'bottom-right')"
          :key="toast.id"
          :category="toast.category"
          :title="toast.title"
          :content="toast.content"
          :closable="toast.closable"
          vertical
          @close="store.dismiss(toast.id)"
        />
      </transition-group>
    </div>
  </teleport>
</template>

<style scoped>
.info-bar-host {
  position: fixed;
  z-index: 200;
  display: flex;
  flex-direction: column;
  /* 条与条之间 16，与 InfoBarManager.spacing 一致 */
  gap: 16px;
  /* 容器不吃事件，只有气泡本身吃（关闭按钮要能点） */
  pointer-events: none;
}

/* margin = 24 */
.info-bar-host.is-top {
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  align-items: center;
}

.info-bar-host.is-bottom-right {
  right: 24px;
  bottom: 24px;
  align-items: flex-end;
}

/* 入场 200ms OutQuad，从上方 16px 滑下来（TopInfoBarManager._slideStartPos） */
.drop-enter-active {
  transition:
    transform 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94),
    opacity 0.2s ease-out;
}

.drop-enter-from {
  transform: translateY(-16px);
  opacity: 0;
}

/* 退场只淡出，200ms（InfoBar.__fadeOut） */
.drop-leave-active {
  transition: opacity 0.2s ease-out;
  /* 离场的那条要脱离文档流，否则下面几条会先等它消失再上移，看着一顿 */
  position: absolute;
}

.drop-leave-to {
  opacity: 0;
}

.drop-move {
  transition: transform 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

/* 右下角那一路从下方滑入 */
.is-bottom-right .drop-enter-from {
  transform: translateY(16px);
}
</style>
