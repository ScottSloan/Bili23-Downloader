<script setup lang="ts">
/**
 * 折叠卡片展开后里面的一行
 *
 * 对应 qfluentwidgets 的 `GroupWidget`（expand_setting_card.py）：
 * 最小高 60，左右内边距 48、上下 12，图标与文字间距 16。
 *
 * 左右 48 的缩进是这套设计里「从属于上面那张卡片」的唯一提示 ——
 * 桌面版**不额外缩进**，也不给子项加边框，行与行之间只有一条 1px 分隔线
 * （分隔线由 ExpandSettingCard 画，不在这里）。
 */
import fluentIcon from '../../icons/FluentIcon.vue'

withDefaults(
  defineProps<{
    title: string
    icon?: string
    description?: string
    disabled?: boolean
    restart?: boolean
    restartHint?: string
  }>(),
  {
    icon: '',
    description: '',
    disabled: false,
    restart: false,
    restartHint: '',
  },
)
</script>

<template>
  <div class="setting-group-row" :class="{ 'is-disabled': disabled }">
    <fluentIcon v-if="icon" :name="icon" class="icon" />

    <div class="text">
      <div class="title">
        {{ title }}
        <span v-if="restart" class="restart-badge" :title="restartHint">{{ restartHint }}</span>
      </div>
      <div v-if="description" class="description">{{ description }}</div>
    </div>

    <div class="control">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.setting-group-row {
  display: flex;
  align-items: center;
  gap: 16px;
  box-sizing: border-box;
  min-height: 60px;
  padding: 12px 48px;
}

.setting-group-row.is-disabled .icon,
.setting-group-row.is-disabled .title,
.setting-group-row.is-disabled .description {
  color: var(--text-disabled);
}

.text {
  flex: 1 1 auto;
  min-width: 0;
}

.title {
  font-size: 14px;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.description {
  margin-top: 2px;
  font-size: 11px;
  color: var(--card-description);
  line-height: 1.35;
}

.restart-badge {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
  color: var(--card-description);
  background-color: var(--subtle-fill-tertiary);
  border: 1px solid var(--control-stroke-default);
  white-space: nowrap;
}

.control {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 窄屏（手机）下 48 的左右缩进会把控件挤没，退到与顶层卡片同一档 */
@media (max-width: 640px) {
  .setting-group-row {
    padding: 12px 16px;
  }
}
</style>
