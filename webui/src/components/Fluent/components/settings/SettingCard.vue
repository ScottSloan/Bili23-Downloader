<script setup lang="ts">
/**
 * 一行设置项：左边标题与说明，右边控件
 *
 * 对应 qfluentwidgets 的 SettingCard。桌面版每一项都长这样，Web 端照搬同一套布局，
 * 用户在两边看到的是同一个东西。
 */
withDefaults(
  defineProps<{
    title: string
    /** 副标题。留空则整行只显示标题，高度自动收窄 */
    description?: string
    /**
     * 依赖项未开启时置灰
     *
     * 与 GUI 一致：关掉「下载弹幕」之后，弹幕格式、嵌入弹幕这些子项会灰掉而不是消失。
     * 消失会让界面在勾选时跳动，也让用户不知道还有这些选项
     */
    disabled?: boolean
    /** 缩进一级，表示从属于上一项 */
    nested?: boolean
    /** 改完要重启后端才生效 */
    restart?: boolean
    restartHint?: string
  }>(),
  {
    description: '',
    disabled: false,
    nested: false,
    restart: false,
    restartHint: '',
  },
)
</script>

<template>
  <div class="setting-card" :class="{ 'is-disabled': disabled, 'is-nested': nested }">
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
.setting-card {
  display: flex;
  align-items: center;
  gap: 16px;
  box-sizing: border-box;
  min-height: 50px;
  padding: 10px 16px;
  border-radius: 6px;

  background-color: var(--control-fill-default);
  border: 1px solid var(--card-stroke-default);
}

.setting-card.is-nested {
  margin-left: 24px;
}

/*
  置灰的是文字与交互能力，卡片底色不动 —— 底色也跟着变淡的话，
  一组子项全灰之后整块区域会像是「加载失败」
*/
.setting-card.is-disabled .text {
  color: var(--text-disabled);
}

.setting-card.is-disabled .title,
.setting-card.is-disabled .description {
  color: var(--text-disabled);
}

.text {
  flex: 1 1 auto;
  min-width: 0;
}

.title {
  font-size: 11pt;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.description {
  margin-top: 2px;
  font-size: 9.5pt;
  color: var(--text-secondary);
  line-height: 1.35;
}

.restart-badge {
  font-size: 8.5pt;
  padding: 1px 6px;
  border-radius: 10px;
  color: var(--text-secondary);
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
</style>
