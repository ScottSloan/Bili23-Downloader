<script setup lang="ts">
/**
 * 主色拆分按钮：左边是主操作，右边一个箭头拉出菜单
 *
 * 对应桌面版解析页那个「解析 ▾」（`IndeterminateProgressSplitPushButton` +
 * `RoundMenu`）。qss 里两半是这样拼的：主体的右侧圆角归零、右边一条
 * `--ThemeColorLight3` 的分隔线，箭头那半的左侧圆角归零、没有左边框。
 *
 * 菜单本身刻意做得最小：一层绝对定位的浮层，点外面或按 Esc 收起。**不做键盘上下选择**
 * —— 目前只有一项，为它实现一整套 roving tabindex 不划算；菜单项本身是原生 button，
 * Tab 走得到、回车能触发，读屏软件也认得。项数多起来再补。
 */
import { onBeforeUnmount, ref, watch } from 'vue'

defineProps<{
  title: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  click: []
}>()

const open = ref(false)
const root = ref<HTMLElement | null>(null)

function onDocumentPointerDown(event: PointerEvent) {
  if (root.value && !root.value.contains(event.target as Node)) {
    open.value = false
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    open.value = false
  }
}

watch(open, (isOpen) => {
  if (isOpen) {
    document.addEventListener('pointerdown', onDocumentPointerDown)
    window.addEventListener('keydown', onKeydown)
  } else {
    document.removeEventListener('pointerdown', onDocumentPointerDown)
    window.removeEventListener('keydown', onKeydown)
  }
})

// 菜单还开着就被卸载（切页）时监听要收回来，否则会一直挂在 document 上
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocumentPointerDown)
  window.removeEventListener('keydown', onKeydown)
})

/** 菜单项点完就收起。交给调用方在插槽里 @click 自己的处理 */
function closeMenu() {
  open.value = false
}

defineExpose({ closeMenu })
</script>

<template>
  <div ref="root" class="split-button">
    <button type="button" class="main" :disabled="disabled" @click="emit('click')">
      {{ title }}
    </button>

    <button
      type="button"
      class="drop"
      :disabled="disabled"
      :aria-expanded="open"
      aria-haspopup="menu"
      :aria-label="title"
      @click="open = !open"
    >
      <svg viewBox="0 0 12 12" aria-hidden="true">
        <path d="M2 4.5 L6 8.5 L10 4.5" fill="none" stroke="currentColor" stroke-width="1.2" />
      </svg>
    </button>

    <div v-if="open" class="menu" role="menu" @click="closeMenu">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.split-button {
  position: relative;
  display: inline-flex;
  flex: 0 0 auto;
}

.main,
.drop {
  font: inherit;
  margin: 0;
  appearance: none;
  box-sizing: border-box;
  cursor: pointer;
  color: var(--text-on-accent);
  background-color: var(--primary-color);
  border: 1px solid var(--primary-color-light-1);
  border-bottom-color: var(--primary-color-dark-1);
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease;
}

.main {
  padding: 5px 12px 6px 12px;
  /* 「解析」只有两个字，光靠 padding 撑出来的按钮又瘦又高。
     桌面版那个是 PushButton 的默认最小宽度（qfluentwidgets 给 96），这里跟它 */
  min-width: 80px;
  border-radius: 5px 0 0 5px;
  /* 两半之间那条线。qss 里是 --ThemeColorLight3 */
  border-right: 1px solid var(--primary-color-light-3);
}

.drop {
  width: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0 5px 5px 0;
  border-left: none;
}

.drop svg {
  width: 11px;
  height: 11px;
}

.main:not(:disabled):hover,
.drop:not(:disabled):hover {
  background-color: var(--primary-color-light-1);
  border-color: var(--primary-color-light-2);
  border-bottom-color: var(--primary-color-dark-1);
}

.main:not(:disabled):active,
.drop:not(:disabled):active {
  color: color-mix(in srgb, var(--text-on-accent) 63%, transparent);
  background-color: var(--primary-color-light-3);
  border-color: var(--primary-color-light-3);
}

.main:focus-visible,
.drop:focus-visible {
  outline: 2px solid var(--focus-stroke-outer);
  outline-offset: 1px;
  box-shadow: 0 0 0 1px var(--focus-stroke-inner);
  /* 焦点环要压在旁边那半上面，否则会被它盖掉一条边 */
  z-index: 1;
}

.main:disabled,
.drop:disabled {
  cursor: default;
  color: var(--text-on-accent-disabled);
  background-color: var(--accent-fill-disabled);
  border-color: var(--accent-fill-disabled);
}

.main:disabled {
  border-right-color: var(--accent-fill-disabled);
}

/* ---- 菜单 ---- */
.menu {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  z-index: 50;
  min-width: 160px;
  padding: 4px;
  border-radius: 8px;
  background-color: var(--dialog-fill);
  border: 1px solid var(--card-stroke-default);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.18);
}

.menu :deep(button) {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  font: inherit;
  font-size: 14px;
  text-align: left;
  padding: 7px 10px;
  margin: 0;
  appearance: none;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  color: var(--text-primary);
  background-color: transparent;
}

.menu :deep(button:hover) {
  background-color: var(--subtle-fill-secondary);
}

.menu :deep(button:active) {
  background-color: var(--subtle-fill-tertiary);
}
</style>
