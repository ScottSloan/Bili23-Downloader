<script setup lang="ts">
/**
 * 下载选项 · 附加内容页
 *
 * 对应桌面版 `gui/dialog/download_options/additional.py`：弹幕 / 字幕 / 封面 /
 * 章节 / 元数据五张折叠卡片，默认全部展开。
 *
 * ## 这一页改的是全局设置
 *
 * 与桌面版语义一致：那边这五张卡片就是设置页里的同一批 `SettingCard`，绑的是
 * 同一批 `config` 项，在对话框里改完立刻落盘、对以后的下载也生效。
 * 所以这里直接走 `settingsStore`，不做「仅本次」的本地态。
 *
 * 建任务时 `snapshot(options)` 会把当时的全局值固化进 `task_info.Options`，
 * 所以「先写全局设置、再建任务」这条链是自洽的 —— 队列里已有的任务不受影响。
 *
 * ## 卡片定义从设置页那份清单里挑，不复制
 *
 * `settings/spec.ts` 里已经有 `danmaku` / `subtitle` / `cover` / `chapter` /
 * `metadata` 五张卡片的定义（key、图标、每一行的 attr 与依赖关系）。在这里另写一份的话，
 * 加一个新的字幕选项时只会出现在设置页，对话框里没有，而且不报错。
 */
import { computed, ref } from 'vue'
import { useSettingsStore } from '@/stores/settingsStore'
import { t } from '@/i18n'
import { expandCard, type SettingSpec } from '@/components/App/settings/spec'
import { settingSummary } from '@/components/App/settings/summary'
import settingRow from '@/components/App/settings/SettingRow.vue'
import settingDialogHost from '@/components/App/settings/SettingDialogHost.vue'
import expandSettingCard from '@/components/Fluent/components/settings/ExpandSettingCard.vue'

const emit = defineEmits<{
  /** 下载内容变了，通知外壳刷新底部预览条 */
  previewChanged: []
}>()

const store = useSettingsStore()

/** 与桌面版 additional.py 里那五张卡片同序 */
const CARD_KEYS = ['danmaku', 'subtitle', 'cover', 'chapter', 'metadata']

const cards = computed(() => CARD_KEYS.map((key) => expandCard(key)).filter((card) => card !== undefined))

/** 哪几项决定底部预览条上的标签。章节那张卡片的开关是「嵌入章节」 */
const PREVIEW_ATTRS: Record<string, string> = {
  danmaku: 'download_danmaku',
  subtitle: 'download_subtitle',
  cover: 'download_cover',
  chapter: 'embed_chapter',
  metadata: 'download_metadata',
}

const openAttr = ref<string | null>(null)

function summaryOf(spec: SettingSpec) {
  return settingSummary(spec, store)
}

function onChanged() {
  emit('previewChanged')
}

async function onOpenDialog(attr: string) {
  // 候选表可能还没拉过（用户没进过设置页就直接下载）。store 自己去重
  await store.loadChoices()

  openAttr.value = attr
}

defineExpose({
  downloadPreview: () =>
    Object.fromEntries(
      Object.entries(PREVIEW_ATTRS).map(([key, attr]) => [key, Boolean(store.value(attr))]),
    ),

  /**
   * 有没有附加文件要下
   *
   * **章节不算**：它是嵌进视频文件里的，本身不产生独立文件。只勾了「嵌入章节」
   * 而两路流都不下的话，实际什么都不会产出 —— 与桌面版 has_file_to_download() 一致
   */
  hasFileToDownload: () =>
    ['download_danmaku', 'download_subtitle', 'download_cover', 'download_metadata'].some((attr) =>
      Boolean(store.value(attr)),
    ),
})
</script>

<template>
  <div class="additional-page">
    <expandSettingCard
      v-for="card in cards"
      :key="card.key"
      :icon="card.icon"
      :title="t(`settings.card.${card.key}.title`)"
      :description="t(`settings.card.${card.key}.desc`)"
      default-expanded
    >
      <settingRow
        v-for="spec in card.items"
        :key="spec.attr"
        :spec="spec"
        :summary="summaryOf(spec)"
        in-group
        @changed="onChanged"
        @open-dialog="onOpenDialog"
      />
    </expandSettingCard>

    <settingDialogHost :attr="openAttr" @close="openAttr = null" @saved="onChanged" />
  </div>
</template>

<style scoped>
.additional-page {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
</style>
