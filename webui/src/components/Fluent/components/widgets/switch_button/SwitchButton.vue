<script setup lang="ts">
/**
 * Fluent 的开关
 *
 * 底下是一个真的 `<input type="checkbox">`，外观全靠兄弟元素画。
 * 不用 div + role="switch" 手搓的理由和 PushButton 一样：原生控件自带 Tab 可达、
 * 空格切换、禁用语义、以及读屏软件认得的状态，手搓的每一样都要重新实现一遍且容易漏。
 */
withDefaults(
  defineProps<{
    modelValue?: boolean
    disabled?: boolean
    /** 无障碍名称。设置项里开关旁边的标题不在同一个 label 里，必须显式给 */
    label?: string
    /**
     * 开关左侧那两个字（开 / 关）
     *
     * 桌面版的 SwitchSettingCard 一律带着它（`SwitchButton(tr('Off'), ...)`，
     * IndicatorPosition.RIGHT 表示文字在左）。两个都留空就不显示 ——
     * 对话框里那些紧凑的开关不需要它
     */
    onText?: string
    offText?: string
  }>(),
  {
    modelValue: false,
    disabled: false,
    label: '',
    onText: '',
    offText: '',
  },
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
}>()

function handleChange(event: Event) {
  emit('update:modelValue', (event.target as HTMLInputElement).checked)
}
</script>

<template>
  <label class="fluent-switch" :class="{ 'is-disabled': disabled }">
    <input
      type="checkbox"
      role="switch"
      :checked="modelValue"
      :disabled="disabled"
      :aria-label="label || undefined"
      @change="handleChange"
    />
    <span v-if="onText || offText" class="state">{{ modelValue ? onText : offText }}</span>
    <span class="track"><span class="thumb"></span></span>
  </label>
</template>

<style scoped>
.fluent-switch {
  position: relative;
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  cursor: pointer;
}

.fluent-switch.is-disabled {
  cursor: default;
}

/* 输入框只保留功能，视觉全交给 .track —— 但不能用 display:none，
   那会让它从无障碍树和 Tab 序里一起消失 */
.fluent-switch input {
  position: absolute;
  inset: 0;
  margin: 0;
  opacity: 0;
  cursor: inherit;
}

/* 文字与滑轨之间 12 —— 对应 switch_button.qss 里的 qproperty-spacing: 12 */
.state {
  font-size: 14px;
  margin-right: 12px;
  color: var(--text-primary);
  user-select: none;
}

.fluent-switch.is-disabled .state {
  color: var(--text-disabled);
}

.track {
  box-sizing: border-box;
  width: 40px;
  height: 20px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  padding: 0 3px;
  transition:
    background-color 0.15s ease,
    border-color 0.15s ease;

  background-color: var(--control-fill-tertiary);
  border: 1px solid var(--control-stroke-input);
}

.thumb {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: var(--text-secondary);
  /* 关到开是位移而不是左右外边距切换，这样 transform 能走 GPU 合成 */
  transform: translateX(0);
  transition:
    transform 0.15s cubic-bezier(0.16, 1, 0.3, 1),
    background-color 0.15s ease,
    width 0.1s ease;
}

.fluent-switch:hover .track {
  background-color: var(--control-fill-secondary);
}

/* 按下时滑块拉长一点，Fluent 的手感来源 */
.fluent-switch:active:not(.is-disabled) .thumb {
  width: 17px;
  border-radius: 6px;
}

/* ---- 打开 ---- */
.fluent-switch input:checked + .track {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
}

.fluent-switch input:checked + .track .thumb {
  background-color: var(--text-on-accent);
  transform: translateX(20px);
}

.fluent-switch:active:not(.is-disabled) input:checked + .track .thumb {
  /* 滑块变宽后右端会越界，位移相应减去多出来的宽度 */
  transform: translateX(15px);
}

.fluent-switch:hover input:checked + .track {
  background-color: var(--primary-color-light-1);
  border-color: var(--primary-color-light-1);
}

/* ---- 键盘焦点：双环，与 PushButton 同一套 ---- */
.fluent-switch input:focus-visible + .track {
  outline: 2px solid var(--focus-stroke-outer);
  outline-offset: 2px;
  box-shadow: 0 0 0 1px var(--focus-stroke-inner);
}

/* ---- 禁用 ---- */
.fluent-switch input:disabled + .track {
  background-color: var(--control-fill-tertiary);
  border-color: var(--accent-fill-disabled);
}

.fluent-switch input:disabled + .track .thumb {
  background-color: var(--text-disabled);
}

.fluent-switch input:checked:disabled + .track {
  background-color: var(--accent-fill-disabled);
  border-color: var(--accent-fill-disabled);
}

.fluent-switch input:checked:disabled + .track .thumb {
  background-color: var(--text-on-accent-disabled);
}
</style>
