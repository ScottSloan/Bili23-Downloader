<script setup lang="ts">
/** 一组设置项。对应 qfluentwidgets 的 SettingCardGroup：组标题 + 若干张卡片 */
defineProps<{
  title: string
}>()
</script>

<template>
  <section class="setting-card-group">
    <h2>{{ title }}</h2>

    <div class="cards">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.setting-card-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

h2 {
  margin: 0;
  font-size: 12pt;
  font-weight: 600;
  color: var(--text-primary);
}

.cards {
  display: flex;
  flex-direction: column;
  /* 卡片之间只留 2px，看起来是连成一体的一段，与桌面版一致 */
  gap: 2px;
}
</style>
