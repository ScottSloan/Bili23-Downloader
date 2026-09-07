<script setup lang="ts">
/**
 * 一行设置项：左边图标、标题与说明，右边控件
 *
 * 对应 qfluentwidgets 的 `SettingCard`（components/settings/setting_card.py）。
 * 尺寸与配色照着那边抄：
 *
 * - 高 70（带说明）/ 50（不带），左右各 16 内边距，图标 16×16，图标与文字间距 16
 * - 圆角 6，底色 --card-fill-default，描边 --card-stroke-default
 * - 标题 14px，说明 11px 且用单独的一档灰
 *
 * 桌面版用的是 `setFixedHeight`，这里写成 min-height：浏览器窗口可以窄到让说明文字
 * 折行，定死高度会把第二行裁掉。
 */
import fluentIcon from '../../icons/FluentIcon.vue'

withDefaults(
  defineProps<{
    title: string
    /** 左侧图标名，见 icons/settingIcons.ts。不给则不占位 */
    icon?: string
    /** 副标题。留空则整行只显示标题，高度收窄到 50 */
    description?: string
    /**
     * 依赖项未开启时置灰
     *
     * 与 GUI 一致：关掉「下载弹幕」之后，弹幕格式、嵌入弹幕这些子项会灰掉而不是消失。
     * 消失会让界面在勾选时跳动，也让用户不知道还有这些选项
     */
    disabled?: boolean
    /** 改完要重启后端才生效 */
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
  <div class="setting-card" :class="{ 'is-disabled': disabled, 'has-description': description }">
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
.setting-card {
  display: flex;
  align-items: center;
  gap: 16px;
  box-sizing: border-box;
  min-height: 50px;
  padding: 0 16px;
  border-radius: 6px;

  background-color: var(--card-fill-default);
  border: 1px solid var(--card-stroke-default);
}

.setting-card.has-description {
  min-height: 70px;
  /* 文字折行时上下留点余量，不折行时高度仍由 min-height 决定 */
  padding-top: 10px;
  padding-bottom: 10px;
}

/*
  置灰的是文字与交互能力，卡片底色不动 —— 底色也跟着变淡的话，
  一组子项全灰之后整块区域会像是「加载失败」
*/
.setting-card.is-disabled .icon,
.setting-card.is-disabled .title,
.setting-card.is-disabled .description {
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
</style>
