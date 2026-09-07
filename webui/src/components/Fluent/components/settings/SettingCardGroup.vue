<script setup lang="ts">
/**
 * 一组设置项。对应 qfluentwidgets 的 `SettingCardGroup`
 *
 * 度量抄自 `setting_card_group.py`：组标题 20px 常规字重，标题与卡片之间 12，
 * 卡片之间 2。卡片之间只留 2px 是有意的 —— 一组卡片看起来是连成一段的，
 * 与组之间的 28px 形成层级。
 */
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
  gap: 12px;
}

h2 {
  margin: 0;
  font-size: 20px;
  /* 常规字重，不是 600 —— 桌面版的 setFont(label, 20) 用的是 QFont.Normal */
  font-weight: 400;
  color: var(--text-primary);
}

.cards {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
</style>
