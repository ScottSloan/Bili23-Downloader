<script setup lang="ts">
/**
 * 下载选项对话框
 *
 * 对应桌面版 `gui/dialog/download_options/dialog.py`：三个页签（媒体设置 / 附加内容 /
 * 下载设置）+ 底部一条实时预览「这次将要下载什么」的彩色标签。
 *
 * ## 两个入口，两种模式
 *
 * 与桌面版一样：
 *
 * - **download**：点「下载」时弹出，确定后建任务
 * - **configure**：解析页工具栏那个按钮，确定后**只保存设置、不建任务** ——
 *   用途是下载之前先把选项调好
 *
 * 在此之前 Web 端的工具按钮是直接跳去设置页的，理由写在 ParseView 里
 * （「全局选项归设置页」）。那个理由不成立：这三页里有一半的项**只对这一次下载生效**
 * （画质、编码、命名规则），设置页里根本没有它们的位置。
 *
 * ## 三页的存储去向不同，这是照抄桌面版而不是没统一
 *
 * | 页 | 去向 |
 * |---|---|
 * | 媒体设置 | 随 `options` 传给建任务接口（仅本次）+ localStorage 记作下次的预选值 |
 * | 附加内容 | 直接写 `/api/settings`（全局，与设置页同一批 attr） |
 * | 下载设置 | 目录 / 格式 / 编号方式写全局；命名规则随 options |
 *
 * 桌面版就是这么分的（媒体那几项是运行时属性，附加内容那些是持久化配置项）。
 * 强行统一成一种反而会改掉用户已经习惯的行为。
 */
import { computed, ref, useTemplateRef, watch } from 'vue'
import { tasks as tasksApi, ApiError } from '@/api'
import { t } from '@/i18n'
import { useSettingsStore } from '@/stores/settingsStore'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import fluentPivot from '@/components/Fluent/components/navigation/FluentPivot.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import mediaPage from './MediaPage.vue'
import additionalPage from './AdditionalPage.vue'
import downloadPage from './DownloadPage.vue'
import previewBar from './PreviewBar.vue'
import confirmDialog from './ConfirmDialog.vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    /** 已勾选的剧集，原样来自解析结果的叶子。configure 模式下为空 */
    episodes?: Record<string, unknown>[]
    /**
     * 媒体信息预览用哪几集
     *
     * **与 episodes 分开**，这一点与桌面版一致：那边预览的是「链接指向的那一集，
     * 否则列表第一个」，与勾选无关，所以两个入口（下载 / 仅配置）看到的媒体信息
     * 是同一份。此前 Web 端把勾选项直接当候选，于是不勾就没有画质可选，
     * 工具栏那个入口更是压根没有媒体信息
     */
    candidates?: Record<string, unknown>[]
    mode?: 'download' | 'configure'
  }>(),
  {
    episodes: () => [],
    candidates: () => [],
    mode: 'download',
  },
)

const emit = defineEmits<{
  close: []
  created: [count: number]
  /** configure 模式下点了确定 */
  saved: []
}>()

const settingsStore = useSettingsStore()

const tab = ref('media')

const submitting = ref(false)
const error = ref('')

const media = useTemplateRef<InstanceType<typeof mediaPage>>('media')
const additional = useTemplateRef<InstanceType<typeof additionalPage>>('additional')
const download = useTemplateRef<InstanceType<typeof downloadPage>>('download')

const tabs = computed(() => [
  { key: 'media', label: t('downloadOptions.tab.media'), icon: 'media' },
  { key: 'additional', label: t('downloadOptions.tab.additional'), icon: 'document' },
  { key: 'download', label: t('downloadOptions.tab.download'), icon: 'download' },
])

/**
 * 命名规则按哪一类媒体筛选
 *
 * 取自**预览的那一集**而不是勾选的第一项 —— 与桌面版一致（那边读的是
 * `PreviewerInfo.attribute`，也就是刚预览过的那个）。两者同属一棵解析树，
 * 位标志本来就一样；但「仅配置」模式下没有勾选项，只有候选
 */
const attribute = computed(() => {
  const first = props.candidates[0] as { attribute?: number } | undefined

  return typeof first?.attribute === 'number' ? first.attribute : undefined
})

// ---------------- 底部预览条 ----------------

const previewState = ref<Record<string, boolean>>({})

function refreshPreview() {
  previewState.value = {
    ...(media.value?.downloadPreview() ?? {}),
    ...(additional.value?.downloadPreview() ?? {}),
  }
}

// 附加内容页改的是 store 里的值，用 watch 兜住「不是点开关而是从对话框存回来」的路径
watch(
  () => settingsStore.items,
  () => refreshPreview(),
  { deep: true },
)

// ---------------- 打开时初始化 ----------------

watch(
  () => props.open,
  async (open) => {
    if (!open) {
      return
    }

    tab.value = 'media'
    error.value = ''

    // 附加内容页与下载设置页读的都是全局设置，必须先有值
    await settingsStore.load()

    await Promise.all([media.value?.load(), download.value?.load()])

    refreshPreview()
  },
)

// ---------------- 确认前的提醒 ----------------

type Notice = 'silent' | 'unmerged' | 'nothing'

const notice = ref<Notice | null>(null)

/** 用户已经确认过的提醒。同一次打开里不重复问 */
const acknowledged = ref<Set<Notice>>(new Set())

/**
 * 该不该拦一下
 *
 * 与桌面版 `MediaSettingsPage.on_check()` 逐条对齐，顺序也一样：
 * 先问「只下视频会没声音」，再问「没开合并会得到两个文件」
 */
function nextNotice(): Notice | null {
  const state = media.value?.state

  if (!state) {
    return null
  }

  if (!state.download_audio_stream && state.download_video_stream) {
    return 'silent'
  }

  if (!state.merge_video_audio && state.download_video_stream && state.download_audio_stream) {
    return 'unmerged'
  }

  return null
}

const noticeTitle = computed(() =>
  notice.value === 'nothing'
    ? t('downloadOptions.notice.nothingTitle')
    : t('downloadOptions.notice.title'),
)

const noticeContent = computed(() =>
  notice.value ? t(`downloadOptions.notice.${notice.value}`) : '',
)

function onNoticeConfirm() {
  const current = notice.value

  notice.value = null

  if (!current || current === 'nothing') {
    // 「什么都没选」只是告知，确定之后回到对话框继续改
    return
  }

  acknowledged.value.add(current)

  void confirm()
}

// ---------------- 确定 ----------------

async function confirm() {
  error.value = ''

  const pending = nextNotice()

  if (pending && !acknowledged.value.has(pending)) {
    notice.value = pending

    return
  }

  // 一路流都不下、附加文件也一个不选 —— 这么点下去什么都不会产出
  const hasMedia = media.value?.hasMediaToDownload() ?? false
  const hasFiles = additional.value?.hasFileToDownload() ?? false

  if (!hasMedia && !hasFiles) {
    notice.value = 'nothing'

    return
  }

  media.value?.save()

  // 附加内容与下载设置写的是全局设置，攒着的那批改动要先落盘再建任务 ——
  // 否则 snapshot() 固化下来的还是改动之前的值
  await settingsStore.flush()

  if (props.mode === 'configure') {
    emit('saved')
    emit('close')

    return
  }

  submitting.value = true

  try {
    const result = await tasksApi.create(props.episodes, {
      ...(media.value?.options() ?? {}),
      ...(download.value?.options() ?? {}),
    })

    emit('created', result.created)
    emit('close')
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : String(e)
  } finally {
    submitting.value = false
  }
}

function cancel() {
  acknowledged.value = new Set()

  emit('close')
}
</script>

<template>
  <fluentDialog
    :open="open"
    :title="t('downloadOptions.title')"
    width="780px"
    :close-on-mask="false"
    @close="cancel"
  >
    <fluentPivot v-model="tab" :items="tabs" class="tabs" />

    <div class="stack">
      <!--
        三页都常驻，用 v-show 切换而不是 v-if：媒体页那边有现查的档位与流详情，
        每切一次页签就重新拉一遍既慢又会把用户选好的档位重置掉
      -->
      <mediaPage
        v-show="tab === 'media'"
        ref="media"
        :candidates="candidates"
        @preview-changed="refreshPreview"
      />

      <additionalPage v-show="tab === 'additional'" ref="additional" @preview-changed="refreshPreview" />

      <downloadPage
        v-show="tab === 'download'"
        ref="download"
        :attribute="attribute"
        :per-batch="mode === 'download'"
      />
    </div>

    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <template #actions>
      <previewBar :state="previewState" class="preview" />

      <div class="actions">
        <primaryPushButton
          :title="submitting ? t('downloadOptions.submitting') : t('settings.dialog.ok')"
          :disabled="submitting"
          @click="confirm"
        />
        <pushButton :title="t('settings.dialog.cancel')" @click="cancel" />
      </div>
    </template>
  </fluentDialog>

  <confirmDialog
    :open="notice !== null"
    :title="noticeTitle"
    :content="noticeContent"
    :ok-only="notice === 'nothing'"
    @confirm="onNoticeConfirm"
    @cancel="notice = null"
  />
</template>

<style scoped>
/* 与桌面版一致：页签在标题下面、内容区上面，左侧与内容对齐 */
.tabs {
  flex: 0 0 auto;
}

.stack {
  flex: 1 1 auto;
  min-height: 0;
  /* 桌面版整个对话框固定 750×500，内容区放不下就滚。这里跟着来，
     但高度用 vh 兜住小屏：写死 500 的话手机上底部按钮会被挤出视口 */
  height: min(56vh, 420px);
  overflow-y: auto;
  /* 卡片的焦点环画在边框上，不留一点内边距会被滚动容器裁掉 */
  padding: 2px;
  margin: 0 -2px;
}

.error {
  flex: 0 0 auto;
  margin: 0;
  font-size: 12px;
  color: var(--text-danger);
}

/*
  底部一行：左边预览条，右边两个按钮。

  FluentDialog 的 `.footer > button { flex: 1 1 0 }` 会让按钮等分整行宽度，
  那是给「两个按钮撑满」的对话框用的。这里包一层 div 就不再命中那条规则
  （它要求是 footer 的直接子元素），按钮回到自然宽度
*/
.preview {
  flex: 1 1 auto;
  min-width: 0;
}

.actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.actions :deep(button) {
  min-width: 80px;
}
</style>
