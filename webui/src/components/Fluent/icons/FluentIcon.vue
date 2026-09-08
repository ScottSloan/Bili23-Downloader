<script setup lang="ts">
/**
 * 按名字画一个设置页图标
 *
 * 路径数据来自 `fluentIcons.ts`（由 scripts/gen_webui_icons.py 从 Qt 资源生成），
 * 与桌面版设置页用的是同一批图形。导航栏那几个手写的 IconXxx.vue 保持原样 ——
 * 它们只有四个，且各自带着自己的注释。
 *
 * 名字认不出来就什么都不画：清单里换了个图标名不至于让整页崩掉，
 * 顶多是那张卡片左边空一块。
 */
import { computed } from 'vue'
import { FLUENT_ICONS } from './fluentIcons'

const props = defineProps<{
  name?: string
}>()

const icon = computed(() => (props.name ? FLUENT_ICONS[props.name] : undefined))
</script>

<template>
  <!-- eslint-disable vue/no-v-html -->
  <!--
    v-html 的内容是构建期生成的本地常量，不含任何外部输入。
    改成一堆 <path> 组件的话，那些带 transform 的分组（qfluentwidgets 的图标大多有两层）
    还得在这儿重新拼一遍，抄错了没人看得出来
  -->
  <svg
    v-if="icon"
    class="fluent-icon"
    xmlns="http://www.w3.org/2000/svg"
    :viewBox="icon.viewBox"
    aria-hidden="true"
    focusable="false"
    v-html="icon.body"
  />
</template>

<style scoped>
.fluent-icon {
  /* 桌面版给图标定死 16x16（SettingCard.setIconSize），这里跟着写死，
     不用 1em —— 卡片标题的字号将来若变了，图标不该跟着变大 */
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
  color: var(--text-primary);
}
</style>
