<script setup lang="ts">
/**
 * 只有图标的普通按钮
 *
 * 对应 qfluentwidgets 的 `ToolButton`：外观与 `PushButton` 完全一样（同一条 qss 规则），
 * 只是内边距换成 `5px 9px 6px 8px`、里面放一个 16×16 的图标。
 *
 * 与 `TransparentToolButton` 的区别是**有底色有边框**。桌面版下载页工具栏上
 * 排序与打开目录用的是这个，解析页工具栏那四个用的是透明的那个。
 *
 * 样式复用 `PushButton`：把它当壳，图标塞进默认插槽 —— 两套 qss 本来就是同一条规则，
 * 抄第二遍迟早会分叉。
 */
import pushButton from './PushButton.vue'
import fluentIcon from '../../../icons/FluentIcon.vue'

withDefaults(
  defineProps<{
    /** 图标名，见 icons/fluentIcons.ts */
    icon: string
    /** 无障碍名称，同时作为鼠标悬停的气泡提示。图标按钮不给名字，读屏软件念出来是空的 */
    label: string
    disabled?: boolean
    variant?: 'push' | 'primary'
  }>(),
  {
    disabled: false,
    variant: 'push',
  },
)
</script>

<template>
  <pushButton
    class="fluent-tool-button"
    :variant="variant"
    :disabled="disabled"
    :aria-label="label"
    :title="label"
  >
    <fluentIcon :name="icon" />
  </pushButton>
</template>

<style scoped>
/* :deep 是因为样式要落在 PushButton 的根元素上 */
.fluent-tool-button {
  padding: 5px 9px 6px 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
</style>
