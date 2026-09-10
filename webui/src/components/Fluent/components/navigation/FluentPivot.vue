<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch, nextTick } from 'vue'
import fluentIcon from '../../icons/FluentIcon.vue'

interface PivotItem {
  key: string
  label: string
  /** 可选的行首图标。桌面版的下载选项对话框三个页签都带图标，设置页那些不带 */
  icon?: string
}

const props = defineProps<{
  items: PivotItem[]
  modelValue: string
}>()

const emit = defineEmits<{
  'update:modelValue': [key: string]
}>()

const rootRef = ref<HTMLElement | null>(null)
const itemRefs = ref<HTMLElement[]>([])

const indicator = ref({ left: 0, ready: false })

// 指示条长度，与 Pivot._indicatorLength 一致
const INDICATOR_LENGTH = 16

const activeIndex = computed(() => props.items.findIndex((item) => item.key === props.modelValue))

function measure() {
  const index = activeIndex.value

  if (index < 0) {
    indicator.value = { left: 0, ready: false }

    return
  }

  const element = itemRefs.value[index]
  const root = rootRef.value

  if (!element || !root) {
    return
  }

  const left =
    element.offsetLeft + Math.round(element.offsetWidth / 2) - Math.floor(INDICATOR_LENGTH / 2)

  indicator.value = { left, ready: true }
}

// 字体加载完、窗口变宽窄，项的宽度都会变，指示条要跟着挪。
// 只在挂载后建一次，不用逐项监听
let observer: ResizeObserver | null = null

onMounted(async () => {
  await nextTick()

  measure()

  if (typeof ResizeObserver !== 'undefined' && rootRef.value) {
    observer = new ResizeObserver(() => measure())

    observer.observe(rootRef.value)
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()

  observer = null
})

watch(
  () => [props.modelValue, props.items.map((item) => item.label).join('|')],
  async () => {
    await nextTick()

    measure()
  },
)

function setItemRef(element: unknown, index: number) {
  if (element instanceof HTMLElement) {
    itemRefs.value[index] = element
  }
}

function onKeydown(event: KeyboardEvent) {
  const index = activeIndex.value

  if (index < 0) {
    return
  }

  // WAI-ARIA 的 tab 模式：左右键在标签之间移动并立即切换
  const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0

  if (!step) {
    return
  }

  event.preventDefault()

  const next = (index + step + props.items.length) % props.items.length

  emit('update:modelValue', props.items[next].key)

  nextTick(() => itemRefs.value[next]?.focus())
}
</script>

<template>
  <div ref="rootRef" class="fluent-pivot" role="tablist" @keydown="onKeydown">
    <button
      v-for="(item, index) in items"
      :key="item.key"
      :ref="(element) => setItemRef(element, index)"
      type="button"
      role="tab"
      class="pivot-item"
      :class="{ 'is-selected': item.key === modelValue }"
      :aria-selected="item.key === modelValue"
      :tabindex="item.key === modelValue ? 0 : -1"
      @click="emit('update:modelValue', item.key)"
    >
      <fluentIcon v-if="item.icon" :name="item.icon" class="pivot-icon" />
      <span>{{ item.label }}</span>
    </button>

    <span
      v-show="indicator.ready"
      class="indicator"
      :style="{ transform: `translateX(${indicator.left}px)` }"
    />
  </div>
</template>

<style scoped>
.fluent-pivot {
  position: relative;
  display: flex;
  flex-direction: row;
  align-items: flex-end;
  flex: 0 0 auto;
  gap: 24px;
  /* 指示条占掉底下 3px */
  padding-bottom: 3px;
}

.pivot-item {
  display: flex;
  align-items: center;
  /* 图标与文字 8px，与 qfluentwidgets 的 PivotItem 一致 */
  gap: 8px;
  padding: 10px 12px;
  font: inherit;
  font-size: 15px;
  line-height: 1.2;
  margin: 0;
  appearance: none;
  border: none;
  background-color: transparent;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  color: var(--text-primary);
  transition: color 0.1s ease;
}

/* 选中与否文字颜色相同 —— 桌面版就是这样，区分靠指示条 */
.pivot-item:hover {
  color: var(--text-secondary);
}

.pivot-item:active {
  color: var(--text-tertiary);
}

.pivot-item:focus-visible {
  outline: 2px solid var(--focus-stroke-outer);
  outline-offset: -2px;
  border-radius: 5px;
}

.pivot-icon {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
}

.indicator {
  position: absolute;
  left: 0;
  bottom: 0;
  width: 16px;
  height: 3px;
  border-radius: 1.5px;
  pointer-events: none;
  background-color: var(--primary-color);
  transition: transform 0.2s cubic-bezier(0, 0, 0, 1);
}
</style>
