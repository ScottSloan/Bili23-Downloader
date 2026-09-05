<script setup lang="ts">
const checkboxId = `transparent-checkbox-${Math.random().toString(36).slice(2, 10)}`

defineProps({
  checked: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:checked'])

function handleChange(event: Event) {
  emit('update:checked', (event.target as HTMLInputElement).checked)
}
</script>

<template>
  <div class="transparent-checkbox">
    <input :id="checkboxId" type="checkbox" :checked="checked" @change="handleChange" />
    <label :for="checkboxId"></label>
  </div>
</template>

<style scoped>
.transparent-checkbox {
  position: relative;
  flex: 0 0 auto;
  width: 24px;
  height: 24px;
}

.transparent-checkbox input[type='checkbox'] {
  opacity: 0;
  position: absolute;
  inset: 0;
  margin: 0;
  cursor: pointer;
}

/*
  下面几处 rgba 是有意保留的：它们描述的是「毛玻璃材质」本身（透光、高光、投影），
  用于浮在封面图之上时保证可见性，与深浅主题无关，因此不走 design token
*/
.transparent-checkbox input[type='checkbox'] + label {
  display: block;
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  border: 1px solid rgba(0, 0, 0, 0.35);
  border-radius: 4px;
  position: relative;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.14);
  -webkit-backdrop-filter: blur(8px);
  backdrop-filter: blur(8px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.2),
    0 4px 10px rgba(0, 0, 0, 0.08);
  transition:
    background-color 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    transform 0.18s ease;
}

.transparent-checkbox input[type='checkbox'] + label::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.28), rgba(255, 255, 255, 0));
  pointer-events: none;
}

.transparent-checkbox input[type='checkbox']:checked + label {
  background: var(--primary-color);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.25),
    0 4px 10px rgba(0, 0, 0, 0.12);
}

.transparent-checkbox input[type='checkbox']:checked + label {
  border-color: var(--primary-color-dark-1);
}

:root[data-theme='dark'] .transparent-checkbox input[type='checkbox']:checked + label {
  border-color: var(--primary-color-dark-3);
}

.transparent-checkbox input[type='checkbox']:checked + label::before {
  opacity: 0.18;
}

.transparent-checkbox input[type='checkbox']:checked + label::after {
  content: '';
  position: absolute;
  left: 8px;
  top: 3px;
  width: 5px;
  height: 10px;
  transform: rotate(45deg);
}

.transparent-checkbox input[type='checkbox']:checked + label::after {
  border-right: 2px solid var(--text-on-accent);
  border-bottom: 2px solid var(--text-on-accent);
}

.transparent-checkbox input[type='checkbox']:focus-visible + label {
  outline: 2px solid var(--primary-color-light-2);
  outline-offset: 2px;
}
</style>
