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
})

const emit = defineEmits(['update:modelValue', 'submit'])
</script>

<template>
  <input
    class="fluent-line-edit"
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
  font-size: 11pt;
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

.fluent-line-edit:focus {
  /* 底边加粗 1px，上边距同步减 1px，避免控件整体高度跳动 */
  padding: 6px 10px 5px 10px;
  background-color: var(--control-fill-input-active);
  border-bottom: 2px solid var(--primary-color);
}
</style>
