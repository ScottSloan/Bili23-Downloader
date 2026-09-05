<template>
  <div class="navigation-panel">
    <slot />
  </div>
</template>

<style scoped>
.navigation-panel {
  flex: 1 1 auto;
  min-height: 0;
  width: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  border-top-left-radius: 10px;

  border: 1px solid var(--card-stroke-default);
  border-right: none;
  border-bottom: none;
  background-color: var(--layer-fill-default);
}
</style>
