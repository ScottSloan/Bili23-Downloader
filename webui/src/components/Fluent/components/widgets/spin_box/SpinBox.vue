<script setup lang="ts">
import { ref, watch } from 'vue'

/**
 * 数字输入框
 *
 * ## 为什么不在每次按键时就往外发值
 *
 * 端口范围是 1024–65535。用户想输 8080，第一个键之后框里是 "8" —— 那是个越界值。
 * 如果边打字边 emit，父组件会把 8 存下去、后端把它 clamp 成 1024、再回写进来，
 * 于是输入框里的字在打字过程中被替换掉，第二个键接着 "1024" 打。
 *
 * 所以框里的字是自己的状态，**只在失焦、回车、或点加减按钮时才发出去**。
 * 这也顺带避免了每敲一下就发一次保存请求。
 */
const props = withDefaults(
  defineProps<{
    modelValue?: number
    min?: number
    max?: number
    step?: number
    /** 小数位数。0 表示整数，输入时也会拒绝小数点 */
    decimals?: number
    disabled?: boolean
    label?: string
    suffix?: string
  }>(),
  {
    modelValue: 0,
    min: Number.NEGATIVE_INFINITY,
    max: Number.POSITIVE_INFINITY,
    step: 1,
    decimals: 0,
    disabled: false,
    label: '',
    suffix: '',
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: number): void
}>()

function format(value: number): string {
  return props.decimals > 0 ? value.toFixed(props.decimals) : String(Math.round(value))
}

const text = ref(format(props.modelValue))

// 外部改值（后端纠正、重置为默认值）要反映到框里。
// 只在数值确实不同的时候覆盖，否则用户输 "08" 会被立刻改写成 "8"
watch(
  () => props.modelValue,
  (value) => {
    if (Number.parseFloat(text.value) !== value) {
      text.value = format(value)
    }
  },
)

function clamp(value: number): number {
  return Math.min(props.max, Math.max(props.min, value))
}

/** 把框里的字变成一个合法的值并发出去；认不出来就退回当前值 */
function commit() {
  const parsed = Number.parseFloat(text.value)

  if (!Number.isFinite(parsed)) {
    text.value = format(props.modelValue)

    return
  }

  const value = clamp(props.decimals > 0 ? parsed : Math.round(parsed))

  text.value = format(value)

  if (value !== props.modelValue) {
    emit('update:modelValue', value)
  }
}

function stepBy(delta: number) {
  const base = Number.isFinite(Number.parseFloat(text.value))
    ? Number.parseFloat(text.value)
    : props.modelValue

  const value = clamp(base + delta)

  text.value = format(value)

  if (value !== props.modelValue) {
    emit('update:modelValue', value)
  }
}
</script>

<template>
  <div class="fluent-spin-box" :class="{ 'is-disabled': disabled }">
    <input
      v-model="text"
      type="text"
      inputmode="decimal"
      :disabled="disabled"
      :aria-label="label || undefined"
      @blur="commit"
      @keyup.enter="commit"
      @keydown.up.prevent="stepBy(step)"
      @keydown.down.prevent="stepBy(-step)"
    />

    <span v-if="suffix" class="suffix">{{ suffix }}</span>

    <!-- 加减按钮不进 Tab 序（tabindex="-1"）：键盘用户按上下箭头就行，
         让 Tab 在一个输入框上停三次只会拖慢导航 -->
    <div class="steppers">
      <button
        type="button"
        tabindex="-1"
        :disabled="disabled"
        aria-hidden="true"
        @click="stepBy(step)"
      >
        <svg viewBox="0 0 12 12">
          <path d="M2.5 7.5 L6 4 L9.5 7.5" fill="none" stroke="currentColor" stroke-width="1.2" />
        </svg>
      </button>
      <button
        type="button"
        tabindex="-1"
        :disabled="disabled"
        aria-hidden="true"
        @click="stepBy(-step)"
      >
        <svg viewBox="0 0 12 12">
          <path d="M2.5 4.5 L6 8 L9.5 4.5" fill="none" stroke="currentColor" stroke-width="1.2" />
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.fluent-spin-box {
  position: relative;
  display: inline-flex;
  align-items: center;
  flex: 0 0 auto;
  border-radius: 5px;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease;

  background-color: var(--control-fill-default);
  border: 1px solid var(--control-stroke-default);
  border-bottom-color: var(--control-stroke-input);
}

.fluent-spin-box:hover {
  background-color: var(--control-fill-secondary);
}

.fluent-spin-box:focus-within {
  background-color: var(--control-fill-input-active);
  border-bottom: 2px solid var(--primary-color);
  /* 底边加粗 1px，整体高度靠输入框少 1px 内边距补回来 */
  padding-bottom: 0;
}

.fluent-spin-box input {
  font: inherit;
  font-size: 14px;
  box-sizing: border-box;
  width: 78px;
  padding: 6px 4px 6px 10px;
  border: none;
  background: transparent;
  outline: none;
  color: var(--text-primary);
}

.fluent-spin-box:focus-within input {
  padding-bottom: 5px;
}

.suffix {
  font-size: 13px;
  color: var(--text-secondary);
  user-select: none;
  padding-right: 2px;
}

.steppers {
  display: flex;
  flex-direction: column;
  padding: 2px 3px 2px 0;
  gap: 1px;
}

.steppers button {
  appearance: none;
  border: none;
  background: transparent;
  border-radius: 3px;
  padding: 0;
  width: 22px;
  height: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--text-secondary);
}

.steppers button:not(:disabled):hover {
  background-color: var(--subtle-fill-secondary);
  color: var(--text-primary);
}

.steppers button:not(:disabled):active {
  background-color: var(--subtle-fill-tertiary);
}

.steppers svg {
  width: 11px;
  height: 11px;
}

/* ---- 禁用 ---- */
.fluent-spin-box.is-disabled {
  background-color: var(--control-fill-tertiary);
  border-color: var(--control-stroke-default);
}

.fluent-spin-box.is-disabled input,
.fluent-spin-box.is-disabled .suffix,
.steppers button:disabled {
  color: var(--text-disabled);
  cursor: default;
}
</style>
