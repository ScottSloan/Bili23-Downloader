<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'

/**
 * 对话框外壳：遮罩 + 面板 + 标题 + 底部按钮区
 *
 * 对应 GUI 的 `gui/component/dialog.py` 里的 DialogBase。抽出来之前遮罩与面板的那段
 * CSS 已经被抄了三遍，而键盘与滚动这两件事**每抄一遍都会漏**：
 *
 * - Esc 关闭
 * - 打开时锁住背景滚动，否则在手机上滑动对话框会把底下的页面一起滑走
 */
const props = withDefaults(
  defineProps<{
    open: boolean
    title: string
    /** 面板宽度。内容差别很大，交给调用方定 */
    width?: string
    /** 点遮罩是否关闭。有未保存改动的对话框可以关掉这个 */
    closeOnMask?: boolean
  }>(),
  {
    width: '420px',
    closeOnMask: true,
  },
)

const emit = defineEmits<{
  close: []
}>()

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    emit('close')
  }
}

function lockScroll(locked: boolean) {
  if (typeof document === 'undefined') {
    return
  }

  document.body.style.overflow = locked ? 'hidden' : ''
}

watch(
  () => props.open,
  (open) => {
    lockScroll(open)

    if (open) {
      window.addEventListener('keydown', onKeydown)
    } else {
      window.removeEventListener('keydown', onKeydown)
    }
  },
  { immediate: true },
)

// 对话框还开着就被卸载（切页、路由变化）时，监听与滚动锁都要收回来 ——
// 漏掉的话页面会永久卡在不能滚动的状态，而且看不出是谁干的
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)

  lockScroll(false)
})
</script>

<template>
  <div v-if="open" class="mask" @click.self="closeOnMask && emit('close')">
    <div class="dialog" role="dialog" aria-modal="true" :style="{ width }">
      <h2 class="title">{{ title }}</h2>

      <p v-if="$slots.hint" class="hint"><slot name="hint" /></p>

      <div class="body">
        <slot />
      </div>

      <div class="actions">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(0, 0, 0, 0.35);
  z-index: 100;
}

.dialog {
  max-width: 92vw;
  max-height: 82vh;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 22px 24px;
  border-radius: 8px;
  box-sizing: border-box;
  background-color: var(--solid-bg-base);
  border: 1px solid var(--card-stroke-default);
}

.title {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
}

.hint {
  margin: 0;
  font-size: 12px;
  color: var(--text-secondary);
}

/* 内容区自己滚，标题与按钮固定 —— 否则长列表会把确定按钮推到屏幕外 */
.body {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}
</style>
