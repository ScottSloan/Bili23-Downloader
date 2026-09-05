<script setup lang="ts">
defineProps({
  title: {
    type: String,
    required: true,
  },
  variant: {
    type: String,
    default: 'push',
  },
})
</script>

<template>
  <div class="fluent-button" :class="`is-${variant}`">
    <span>{{ title }}</span>
  </div>
</template>

<style scoped>
.fluent-button {
  text-align: center;
  display: inline-block;
  flex: 0 0 auto;
  justify-content: space-between;
  padding: 5px 12px 6px 12px;
  border-radius: 5px;
  cursor: pointer;
  user-select: none;
  transition:
    background-color 0.2s ease,
    color 0.2s ease,
    border-color 0.2s ease;

  color: var(--text-primary);
  background-color: var(--control-fill-default);
  border: 1px solid var(--control-stroke-default);
  /* Fluent 的立体感来自与其余三边不同的那一条：浅色在底边，深色在顶边 */
  border-bottom-color: var(--control-stroke-accent);
}

:root[data-theme='dark'] .fluent-button {
  border-bottom-color: var(--control-stroke-default);
  border-top-color: var(--control-stroke-accent);
}

.fluent-button:hover {
  background-color: var(--control-fill-secondary);
}

.fluent-button:active {
  color: var(--text-pressed);
  background-color: var(--control-fill-tertiary);
  border-bottom-color: var(--control-stroke-default);
}

:root[data-theme='dark'] .fluent-button:active {
  border-top-color: var(--control-stroke-default);
}

/* ---- primary ---- */
.fluent-button.is-primary {
  color: var(--text-on-accent);
  background-color: var(--primary-color);
  border-color: var(--primary-color-light-1);
  border-bottom-color: var(--primary-color-dark-1);
}

:root[data-theme='dark'] .fluent-button.is-primary {
  border-bottom-color: var(--primary-color-light-2);
  border-top-color: var(--primary-color-light-1);
}

.fluent-button.is-primary:hover {
  background-color: var(--primary-color-light-1);
  border-color: var(--primary-color-light-2);
  border-bottom-color: var(--primary-color-dark-1);
}

:root[data-theme='dark'] .fluent-button.is-primary:hover {
  background-color: var(--primary-color-dark-1);
  border-color: var(--primary-color-light-1);
  border-bottom-color: var(--primary-color-light-2);
}

.fluent-button.is-primary:active {
  color: color-mix(in srgb, var(--text-on-accent) 63%, transparent);
  background-color: var(--primary-color-light-3);
  border-color: var(--primary-color-light-3);
}

:root[data-theme='dark'] .fluent-button.is-primary:active {
  background-color: var(--primary-color-dark-2);
  border-color: var(--primary-color-dark-2);
}
</style>
