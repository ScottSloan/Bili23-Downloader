<script setup>
import { nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

const props = defineProps({
  activeIndex: {
    type: Number,
    default: 0,
  },
})

const rootRef = ref(null)
const indicatorStyle = reactive({ top: '15px' })

let resizeObserver = null

const updateIndicatorPosition = () => {
  const rootElement = rootRef.value

  if (!rootElement) {
    return
  }

  const buttons = rootElement.querySelectorAll('.navigation-bar-button')
  const activeButton = buttons[props.activeIndex]

  if (!activeButton) {
    return
  }

  const top = activeButton.offsetTop + (activeButton.offsetHeight - 24) / 2

  indicatorStyle.top = `${top}px`
}

onMounted(async () => {
  await nextTick()
  updateIndicatorPosition()

  if (typeof ResizeObserver !== 'undefined' && rootRef.value) {
    resizeObserver = new ResizeObserver(() => {
      updateIndicatorPosition()
    })

    resizeObserver.observe(rootRef.value)
  }

  window.addEventListener('resize', updateIndicatorPosition)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  window.removeEventListener('resize', updateIndicatorPosition)
})

watch(
  () => props.activeIndex,
  async () => {
    await nextTick()
    updateIndicatorPosition()
  },
)
</script>

<template>
  <div ref="rootRef" class="navigation-bar">
    <div class="navigation-bar-indicator" :style="indicatorStyle"></div>

    <slot />
  </div>
</template>

<style scoped>
.navigation-bar {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 64px;
  background-color: transparent;
  margin: 4px;
}

.navigation-bar-indicator {
  position: absolute;
  left: 0;
  pointer-events: none;
  width: 4px;
  height: 24px;
  border-radius: 999px;
  background: var(--primary-color);
  box-shadow: 0 0 8px color-mix(in srgb, var(--primary-color) 35%, transparent);
  transition: top 280ms cubic-bezier(0.2, 0, 0, 1);
  will-change: top;
  z-index: 1;
}
</style>
