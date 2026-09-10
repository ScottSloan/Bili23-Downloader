<script setup lang="ts">
/**
 * 卡片右下角那个「关于…」链接点开的说明
 *
 * 对应桌面版 `ExpandGroupSettingCard.showGuideMessageBox()` —— 那边是一个内容可滚动的
 * MessageBox，只有一个「确定」。这些说明文字本身取自 core 的 `Translator`
 * （MEDIA_INFO_GUIDE 等），译文直接用 `src/res/i18n/` 里现成的那几份。
 *
 * 正文按空行分段渲染，不用 `white-space: pre-wrap` 硬铺：
 * 原文里的换行是给定宽的 Qt 标签排的，浏览器窗口宽窄不定，照搬会得到一堆长短不齐的短行
 */
import { computed } from 'vue'
import { t } from '@/i18n'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'

const props = defineProps<{
  open: boolean
  title: string
  /** 正文，段落之间用空行分隔 */
  content: string
}>()

const emit = defineEmits<{ close: [] }>()

const paragraphs = computed(() =>
  props.content
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean),
)
</script>

<template>
  <fluentDialog :open="open" :title="title" width="520px" @close="emit('close')">
    <div class="guide">
      <p v-for="(paragraph, index) in paragraphs" :key="index">{{ paragraph }}</p>
    </div>

    <template #actions>
      <primaryPushButton :title="t('settings.dialog.ok')" @click="emit('close')" />
    </template>
  </fluentDialog>
</template>

<style scoped>
.guide {
  /* 说明可能很长（编号方式那条列了三种模式），给它自己的滚动条 */
  max-height: 52vh;
  overflow-y: auto;
  padding-right: 4px;
}

.guide p {
  margin: 0 0 12px 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  /* 段内的单换行（列举项）要保留，段间的空行已经拆成 <p> 了 */
  white-space: pre-line;
}

.guide p:last-child {
  margin-bottom: 0;
}
</style>
