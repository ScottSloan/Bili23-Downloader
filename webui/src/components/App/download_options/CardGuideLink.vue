<script setup lang="ts">
/**
 * 卡片头部那个「关于…」说明链接
 *
 * 对应桌面版 `GuideSettingCardBase.showHyperLinkLabel()`：跟在卡片说明文字后面，
 * 字号单独压到 11，点开一个只有「确定」的说明框。
 *
 * 通过 ExpandSettingCard 的 `#link` 插槽塞进头部 —— 那张卡片的头部为此特意
 * 没有做成一个 `<button>`（理由见它自己的注释）
 */
defineProps<{ text: string }>()

const emit = defineEmits<{ click: [] }>()
</script>

<template>
  <button type="button" class="link" @click="emit('click')">{{ text }}</button>
</template>

<style scoped>
.link {
  font: inherit;
  /* 桌面版给 HyperlinkLabel 单独设成 11px */
  font-size: 11px;
  padding: 0;
  margin: 0;
  border: none;
  appearance: none;
  background: none;
  cursor: pointer;
  white-space: nowrap;
  color: var(--primary-color);
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}

.link:focus-visible {
  outline: 2px solid var(--focus-stroke-outer);
  outline-offset: 2px;
  border-radius: 3px;
}
</style>
