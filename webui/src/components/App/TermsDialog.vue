<script setup lang="ts">
/**
 * 使用条款
 *
 * 对应桌面版 `gui/dialog/main_window/terms.py`，从「关于」里点进来。
 *
 * 正文与桌面版是同一份（`Translator.TERMS_OF_USE`），中文译文直接取自
 * `src/res/i18n/bili23.zh_CN.ts` / `zh_TW.ts` —— **不重新翻译**：
 * 这是一段带法律意味的告知，两端说的必须是同一件事，重译一遍等于凭空造出第二个版本。
 *
 * 分成 5 个段落键（`terms.p1` … `terms.p5`）而不是一整块，是因为 `t()` 只返回字符串，
 * 而这几段之间要留段距。
 *
 * ## 为什么用 v-html
 *
 * 原文里有几处 `<b>` 加粗，标的都是「严禁商业使用」「不绕过付费墙」这类关键条款，
 * 是原文的一部分，去掉会把语气抹平。这些串是**编译期就写死在 i18n 表里的自家文案**，
 * 与用户输入、接口返回没有任何关系，不存在注入面。
 *
 * 桌面版那边点「确定」会记下 `accepted_terms`。这里不记：**WebUI 没有条款同意的门禁**，
 * 这个对话框纯粹是给人看的，写一个没人读的标记只会让人以为它有用
 */
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import { t } from '@/i18n'

defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const PARAGRAPHS = ['terms.p1', 'terms.p2', 'terms.p3', 'terms.p4', 'terms.p5']
</script>

<template>
  <fluentDialog :open="open" :title="t('terms.title')" width="600px" @close="emit('close')">
    <div class="terms">
      <!-- eslint-disable-next-line vue/no-v-html -->
      <p v-for="key in PARAGRAPHS" :key="key" v-html="t(key)" />
    </div>

    <template #actions>
      <primaryPushButton :title="t('settings.dialog.ok')" @click="emit('close')" />
    </template>
  </fluentDialog>
</template>

<style scoped>
.terms {
  flex: 1 1 auto;
  min-height: 0;
  max-height: 52vh;
  overflow-y: auto;
  /* 滚动条别贴着文字 */
  padding-right: 8px;
}

.terms p {
  margin: 0 0 14px 0;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-primary);
}

.terms p:last-child {
  margin-bottom: 0;
}
</style>
