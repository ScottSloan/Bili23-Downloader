<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    title: string
    width?: string
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

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)

  lockScroll(false)
})
</script>

<template>
  <!--
    包一层 transition 才有退场动画。`v-if` 配 CSS animation 只管得了进场：
    元素一旦被移除就当场消失，关对话框会「啪」地断掉
  -->
  <transition name="mask">
    <div v-if="open" class="mask" @click.self="closeOnMask && emit('close')">
      <div class="dialog" role="dialog" aria-modal="true" :style="{ width }">
        <div class="view">
          <h2 class="title">{{ title }}</h2>

          <p v-if="$slots.hint" class="hint"><slot name="hint" /></p>

          <div class="body">
            <slot />
          </div>
        </div>

        <div v-if="$slots.actions" class="footer">
          <slot name="actions" />
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--dialog-mask);
  z-index: 100;
}

.dialog {
  max-width: 92vw;
  max-height: 82vh;
  display: flex;
  flex-direction: column;
  border-radius: 10px;
  overflow: hidden;
  box-sizing: border-box;
  background-color: var(--dialog-fill);
  border: 1px solid var(--dialog-stroke);
  box-shadow: 0 10px 60px rgba(0, 0, 0, 0.196);
}

/* ---- 内容区 ---- */
.view {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 24px 24px 12px 24px;
}

.title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.hint {
  margin: 0;
  font-size: 14px;
  color: var(--text-primary);
  /*
    排成一行，好让调用方把一个按钮塞进这一行的右端（解析记录的「清除记录」就是这样）。
    只有文字时它是唯一的匿名 flex 项，换行照常，与原来没有区别
  */
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 插槽里带过来的按钮一律靠右。插槽内容带的是调用方的 scope，得用 :deep 才够得着 */
.hint > :deep(button) {
  margin-left: auto;
}

.body {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.footer {
  flex: 0 0 auto;
  box-sizing: border-box;
  min-height: 81px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px;
  background-color: var(--dialog-footer-fill);
  border-top: 1px solid var(--dialog-footer-stroke);
}

.footer > :deep(button) {
  flex: 1 1 0;
}

.footer > :deep(button:only-child) {
  flex: 0 0 calc(50% - 6px);
  margin-left: auto;
}

/*
  进场 / 退场

  照桌面版 `MaskDialogBase`：显示是 200ms InSine 的淡入，关闭是 **100ms 淡出**，
  两边时长不一样是那边就这么写的（showEvent 200 / done 100）—— 关得干脆一点，
  不会让人等着动画放完。

  面板多一点位移，那是网页这边加的，Qt 那边只有整体透明度。**退场不带位移**：
  与 Qt 一致，也免得关的时候整个面板往下坠一截，反而更显眼
*/
.mask-enter-active {
  transition: opacity 0.2s cubic-bezier(0.47, 0, 0.745, 0.715);
}

.mask-enter-active .dialog {
  transition: transform 0.2s cubic-bezier(0.47, 0, 0.745, 0.715);
}

.mask-enter-from {
  opacity: 0;
}

.mask-enter-from .dialog {
  transform: translateY(8px);
}

.mask-leave-active {
  transition: opacity 0.1s linear;
}

.mask-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .mask-enter-active,
  .mask-enter-active .dialog,
  .mask-leave-active {
    transition: none;
  }
}
</style>
