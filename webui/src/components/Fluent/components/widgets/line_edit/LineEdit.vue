<script setup lang="ts">
defineProps({
  placeholder: {
    type: String,
    default: '',
  },
  modelValue: {
    type: String,
    default: '',
  },
  /**
   * 原生 input 的 type
   *
   * 口令输入必须能设成 password —— 少了这个 prop，口令会以明文显示在屏幕上。
   * 只开放确实用得到的几种：text / password / search / number
   */
  type: {
    type: String,
    default: 'text',
  },
})

const emit = defineEmits(['update:modelValue', 'submit'])
</script>

<template>
  <!-- autocomplete、name 之类的原生属性经 attrs fallthrough 落到这里，不必逐个声明 -->
  <input
    class="fluent-line-edit"
    :type="type"
    :placeholder="placeholder"
    :value="modelValue"
    @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    @keyup.enter="emit('submit')"
  />
</template>

<style scoped>
.fluent-line-edit {
  border-radius: 5px;
  padding: 6px 10px;
  font-size: 14px;
  font-family: 'Segoe UI', 'Microsoft YaHei', 'PingFang SC';
  outline: none;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease;

  color: var(--text-primary);
  background-color: var(--control-fill-default);
  border: 1px solid var(--control-stroke-default);
  /* 底边更深，提示这里可输入 */
  border-bottom-color: var(--control-stroke-input);
}

.fluent-line-edit::placeholder {
  color: var(--text-placeholder);
  user-select: none;
}

.fluent-line-edit:hover {
  background-color: var(--control-fill-secondary);
}

/* 禁用态：设置页里有若干项要跟着上一项灰掉（代理服务器跟着代理模式），
   少了这段的话它看起来仍然可输入，点进去却打不了字 */
.fluent-line-edit:disabled {
  cursor: default;
  color: var(--text-disabled);
  background-color: var(--control-fill-tertiary);
  border-color: var(--control-stroke-default);
}

.fluent-line-edit:disabled::placeholder {
  color: var(--text-disabled);
}

.fluent-line-edit:focus {
  /* 底边加粗 1px，上边距同步减 1px，避免控件整体高度跳动 */
  padding: 6px 10px 5px 10px;
  background-color: var(--control-fill-input-active);
  border-bottom: 2px solid var(--primary-color);
}
</style>
