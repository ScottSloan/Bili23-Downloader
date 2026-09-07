<script setup lang="ts">
/**
 * 下拉框
 *
 * 用原生 `<select>` 而不是自己搭一个弹出层。**这是有意的取舍**：自搭的下拉要自己实现
 * 键盘导航、首字母跳转、失焦收起、滚动跟随、读屏语义，还要处理弹出层被祖先的
 * `overflow: hidden` 裁掉的问题；原生 select 这些全都有，代价只是展开后的选项列表
 * 没法按 Fluent 的样式画（那部分由系统绘制）。
 *
 * 收起态的样子是能控住的，而设置页里绝大多数时间看到的就是收起态。
 */
export interface ComboBoxOption {
  /** 提交回后端的值。允许数字 —— 后端的枚举有一半是整数 */
  value: string | number
  label: string
}

const props = withDefaults(
  defineProps<{
    modelValue?: string | number | null
    options: ComboBoxOption[]
    disabled?: boolean
    label?: string
  }>(),
  {
    modelValue: null,
    disabled: false,
    label: '',
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: string | number): void
}>()

function handleChange(event: Event) {
  const index = (event.target as HTMLSelectElement).selectedIndex

  // 用下标取回原始值，而不是读 select 的 value —— DOM 里的 value 一律是字符串，
  // 直接回传会把整数枚举变成 "2"，后端的取值校验认不出来就会回落成默认值
  const option = props.options[index]

  if (option) {
    emit('update:modelValue', option.value)
  }
}
</script>

<template>
  <div class="fluent-combo-box" :class="{ 'is-disabled': disabled }">
    <select
      :value="modelValue === null ? undefined : String(modelValue)"
      :disabled="disabled"
      :aria-label="label || undefined"
      @change="handleChange"
    >
      <option v-for="option in options" :key="String(option.value)" :value="String(option.value)">
        {{ option.label }}
      </option>
    </select>

    <svg class="chevron" viewBox="0 0 12 12" aria-hidden="true">
      <path d="M2 4.5 L6 8.5 L10 4.5" fill="none" stroke="currentColor" stroke-width="1.2" />
    </svg>
  </div>
</template>

<style scoped>
.fluent-combo-box {
  position: relative;
  display: inline-flex;
  align-items: center;
  flex: 0 0 auto;
}

.fluent-combo-box select {
  /* 抹掉系统外观，否则 Windows 上会画一个灰色的原生下拉 */
  appearance: none;
  font: inherit;
  box-sizing: border-box;
  min-width: 140px;
  max-width: 260px;
  /* 右侧给箭头留位置 */
  padding: 5px 30px 6px 11px;
  border-radius: 5px;
  cursor: pointer;
  outline: none;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease;

  color: var(--text-primary);
  background-color: var(--control-fill-default);
  border: 1px solid var(--control-stroke-default);
  border-bottom-color: var(--control-stroke-accent);
}

:root[data-theme='dark'] .fluent-combo-box select {
  border-bottom-color: var(--control-stroke-default);
  border-top-color: var(--control-stroke-accent);
}

/*
  展开后的选项由系统绘制，只有 color / background-color 这两条能被采纳。
  深色主题下不写这两条的话，Windows 会给出白底黑字的一片 —— 在深色界面里格外刺眼
*/
.fluent-combo-box option {
  color: var(--text-primary);
  background-color: var(--solid-bg-base);
}

.fluent-combo-box select:not(:disabled):hover {
  background-color: var(--control-fill-secondary);
}

.fluent-combo-box select:not(:disabled):active {
  color: var(--text-pressed);
  background-color: var(--control-fill-tertiary);
}

.fluent-combo-box select:focus-visible {
  outline: 2px solid var(--focus-stroke-outer);
  outline-offset: 1px;
  box-shadow: 0 0 0 1px var(--focus-stroke-inner);
}

.fluent-combo-box select:disabled {
  cursor: default;
  color: var(--text-disabled);
  background-color: var(--control-fill-tertiary);
  border-color: var(--control-stroke-default);
}

.chevron {
  position: absolute;
  right: 9px;
  width: 12px;
  height: 12px;
  color: var(--text-secondary);
  /* 箭头压在 select 上面，点击要能穿透过去 */
  pointer-events: none;
}

.fluent-combo-box.is-disabled .chevron {
  color: var(--text-disabled);
}
</style>
