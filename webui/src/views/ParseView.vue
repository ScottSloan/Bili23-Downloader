<script setup lang="ts">
import { ref, watch } from 'vue'
import fluentLineEdit from '@/components/Fluent/components/widgets/line_edit/LineEdit.vue'
import primarySplitButton from '@/components/Fluent/components/widgets/button/PrimarySplitButton.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import transparentToolButton from '@/components/Fluent/components/widgets/button/TransparentToolButton.vue'
import parseTree from '@/components/App/parse_list/ParseTree.vue'
import searchDialog from '@/components/App/parse_list/SearchDialog.vue'
import batchSelectDialog from '@/components/App/parse_list/BatchSelectDialog.vue'
import parseHistoryDialog from '@/components/App/parse_list/ParseHistoryDialog.vue'
import batchParseDialog from '@/components/App/parse_list/BatchParseDialog.vue'
import fluentIcon from '@/components/Fluent/icons/FluentIcon.vue'
import downloadOptionsDialog from '@/components/App/download_options/DownloadOptionsDialog.vue'
import { useParseStore } from '@/stores/parseStore'
import { useSettingsStore } from '@/stores/settingsStore'
import { useToastStore } from '@/stores/toastStore'
import { tasks as tasksApi, ApiError } from '@/api'
import { t, episodeTypeName } from '@/i18n'

const store = useParseStore()
const settingsStore = useSettingsStore()
const toast = useToastStore()
const url = ref('')

// 解析失败弹气泡，与桌面版一致（那边是 signal_bus.toast.show 发的 "Parse Failed"）。
// store 里那份 error 仍然留着 —— 它是「当前这次解析的状态」，气泡只是把它推到眼前
watch(
  () => store.error,
  (message) => {
    if (message) {
      toast.error(t('toast.parseFailed'), message)
    }
  },
)

const dialogOpen = ref(false)
/**
 * 对话框以哪种模式打开
 *
 * download：点「下载」弹出，确定后建任务。
 * configure：工具栏那个按钮，确定后只保存设置 —— 用途是下载之前先把选项调好，
 * 与桌面版 parse_interface 里那个入口一致
 */
const dialogMode = ref<'download' | 'configure'>('download')
const pendingEpisodes = ref<Record<string, unknown>[]>([])

/**
 * 媒体信息预览用哪几集
 *
 * 与「要下载哪些」分开算：预览看的是这批内容长什么样（链接指向的那一集，
 * 或列表第一个），与勾选无关 —— 两个入口因此看到的是同一份媒体信息，
 * 与桌面版一致
 */
const previewCandidates = ref<Record<string, unknown>[]>([])

// 工具栏那四个按钮各自的对话框。与桌面版 ParseInterface 的 toolbar_layout 一一对应
const searchOpen = ref(false)
const batchSelectOpen = ref(false)
const historyOpen = ref(false)
const batchParseOpen = ref(false)

// 批量解析中途停下。用 ref 而不是普通变量：模板里给普通 let 赋值不会触发重渲染，
// 现在没人渲染它，将来给「停止」按钮加个禁用态就会踩到
const batchStopped = ref(false)

/**
 * 开始批量解析
 *
 * 「自动加入下载列表」交给这里做而不是塞进 store —— 建任务是 store 之外的事。
 * 不传 options，后端就按全局设置取画质与附加内容，与桌面版那个勾选项的语义一致
 */
async function onBatchParse({ urls, autoAdd }: { urls: string[]; autoAdd: boolean }) {
  batchParseOpen.value = false
  batchStopped.value = false

  let created = 0

  await store.parseBatch(urls, {
    interval: Number(settingsStore.value('auto_parse_interval') ?? 2),
    shouldStop: () => batchStopped.value,
    onEach: async (nodes) => {
      if (!autoAdd) {
        return
      }

      // 只取这一条链接刚解析出来的叶子，别把之前几条的又建一遍
      const episodes = nodes
        .flatMap(function collect(node): Record<string, unknown>[] {
          if (node.children?.length) {
            return node.children.flatMap(collect)
          }

          return node.episode && !node.is_node ? [node.episode] : []
        })
        .filter(Boolean)

      if (!episodes.length) {
        return
      }

      try {
        created += (await tasksApi.create(episodes)).created
      } catch {
        // 单条建任务失败不该把整批停下，继续解析后面的
      }
    },
  })

  toast.success(
    t('toast.done'),
    autoAdd
      ? t('parse.batchParse.doneWithTasks', { count: created })
      : t('parse.batchParse.done', { count: store.total }),
  )
}

function onSearch({ keywords, server }: { keywords: string; server: boolean }) {
  searchOpen.value = false

  if (server) {
    void store.serverSearch(keywords)

    return
  }

  const matches = store.searchLocal(keywords)

  if (keywords) {
    toast.info(t('toast.notice'), t('parse.search.matches', { count: matches }))
  }
}

function onBatchSelect(numbers: number[]) {
  batchSelectOpen.value = false

  toast.info(
    t('toast.notice'),
    t('parse.batchSelect.selected', { count: store.batchSelect(numbers) }),
  )
}

/** 历史里点一条：把链接填回输入框并直接解析，省得再点一次 */
function onPickHistory(picked: string) {
  historyOpen.value = false

  url.value = picked

  store.parse(picked)
}

/**
 * 工具栏上的「下载选项」
 *
 * 与桌面版同一个对话框，只是以「仅配置」模式打开：确定之后**不建任务**，
 * 只把设置存下来，用途是下载之前先把画质、附加内容、命名规则这些调好。
 *
 * 在此之前这个按钮是直接跳去设置页的，理由是「全局选项归设置页」。那个理由不成立：
 * 这三页里有一半的项**只对这一次下载生效**（画质、编码、命名规则），
 * 设置页里根本没有它们的位置
 */
function openOptions() {
  pendingEpisodes.value = []
  previewCandidates.value = store.previewCandidates()
  dialogMode.value = 'configure'
  dialogOpen.value = true
}

async function openDownload() {
  // 摘取走后端的 /api/parse/episodes：「树节点不算下载项」这条规则只该有一处
  const episodes = await store.checkedEpisodes()

  if (!episodes.length) {
    toast.warning(t('toast.notice'), t('parse.nothingChecked'))

    return
  }

  pendingEpisodes.value = episodes
  previewCandidates.value = store.previewCandidates()
  dialogMode.value = 'download'

  // 「下载时显示选项对话框」关掉时直接建任务，全部沿用全局设置 —— 与桌面版一致
  // （gui/interface/parse.py 里也是这么分的一条岔路）。
  //
  // 配置可能还没读回来（没进过设置页）：那时按默认值 true 处理，宁可多弹一次窗
  if (settingsStore.loaded && settingsStore.value('show_download_options_dialog') === false) {
    await createDirectly(episodes)

    return
  }

  dialogOpen.value = true
}

/** 不经对话框直接建任务。不传 options，后端就按全局设置取画质与附加内容 */
async function createDirectly(episodes: Record<string, unknown>[]) {
  try {
    const result = await tasksApi.create(episodes)

    onCreated(result.created)
  } catch (e) {
    toast.error(t('toast.parseFailed'), e instanceof ApiError ? e.message : String(e))
  }
}

function onCreated(count: number) {
  // 建出来的可能比勾选的少（重复下载、需要二次解析的会被后端拦掉），如实说
  toast.show(
    count > 0 ? 'success' : 'info',
    t('toast.done'),
    count > 0
      ? t('parse.created', { count, requested: pendingEpisodes.value.length })
      : t('parse.createdNone'),
  )

  // 重新标一遍「已下载」：刚建的这批现在也算了，列表要跟上
  void store.refreshDownloaded()
}

// 新后端没有「取回上次解析结果」的接口 —— 那是 S0 垫片专有的。
// 解析结果只活在这个页面里，刷新即清空

function submit() {
  store.parse(url.value)
}

// 设置在别处也要用（这里判断要不要弹对话框，列配置也在里面），
// 页面挂载时确保读过一次。store 自己会去重，重复调不会多发请求
void settingsStore.load()

// 列配置与桌面版共用 `parse_list_column`，读回来之前先用内置默认列
void store.loadColumns()
</script>

<template>
  <div class="page-view">
    <div class="url-box">
      <fluentLineEdit
        v-model="url"
        :placeholder="t('parse.placeholder')"
        class="flex-stretch"
        @submit="submit"
      />
      <!-- 与桌面版一样是个拆分按钮：主体解析，箭头拉出「批量解析」 -->
      <primarySplitButton
        :title="store.loading ? t('parse.submitting') : t('parse.submit')"
        :disabled="store.loading"
        @click="submit"
      >
        <button type="button" @click="batchParseOpen = true">
          <fluentIcon name="todo" />
          <span>{{ t('parse.batchParse.title') }}</span>
        </button>
      </primarySplitButton>
    </div>

    <!-- 与桌面版 toolbar_layout 同一排：左边条目计数，右边四个透明工具按钮 -->
    <div class="status-bar">
      <span v-if="store.mediaError" class="status error">
        {{ t('parse.mediaUnavailable', { reason: store.mediaError }) }}
      </span>
      <!-- 一条都没勾时不显示「已选 0 项」：那句话在这种时候只是噪声 -->
      <span v-else-if="store.total" class="status">
        {{
          store.checkedCount
            ? t('parse.summary', {
                category: episodeTypeName(store.category),
                total: store.total,
                checked: store.checkedCount,
              })
            : t('parse.summaryPlain', {
                category: episodeTypeName(store.category),
                total: store.total,
              })
        }}
      </span>

      <span v-if="store.batch" class="status">
        {{
          t('parse.batchParse.progress', {
            done: store.batch.done,
            total: store.batch.total,
          })
        }}
      </span>

      <span class="flex-stretch" />

      <pushButton
        v-if="store.batch"
        :title="t('parse.batchParse.stop')"
        @click="batchStopped = true"
      />

      <transparentToolButton
        icon="search"
        :label="t('parse.toolbar.search')"
        :disabled="!store.total"
        @click="searchOpen = true"
      />
      <transparentToolButton
        icon="history"
        :label="t('parse.toolbar.history')"
        @click="historyOpen = true"
      />
      <transparentToolButton
        icon="todo"
        :label="t('parse.toolbar.batchSelect')"
        :disabled="!store.total"
        @click="batchSelectOpen = true"
      />
      <!-- 没解析过就没有媒体信息可看，也没有命名规则可挑 —— 与旁边几个工具按钮同一个判据 -->
      <transparentToolButton
        icon="options"
        :label="t('parse.toolbar.downloadOptions')"
        :disabled="!store.total"
        @click="openOptions"
      />
    </div>

    <parseTree />

    <div v-if="store.total" class="actions">
      <span class="flex-stretch" />

      <!-- 桌面版这里是 PrimaryPushButton（parse.py 的 download_btn），最小宽 120 -->
      <primaryPushButton
        class="download-btn"
        :title="t('parse.download')"
        :disabled="!store.checkedCount"
        @click="openDownload"
      />
    </div>

    <downloadOptionsDialog
      :open="dialogOpen"
      :episodes="pendingEpisodes"
      :candidates="previewCandidates"
      :mode="dialogMode"
      @close="dialogOpen = false"
      @created="onCreated"
      @saved="toast.success(t('toast.done'), t('downloadOptions.saved'))"
    />

    <searchDialog
      :open="searchOpen"
      :server-search-available="store.serverSearchAvailable"
      :current-keyword="store.currentKeyword"
      :paginated="store.paginated"
      @close="searchOpen = false"
      @search="onSearch"
    />

    <batchSelectDialog
      :open="batchSelectOpen"
      @close="batchSelectOpen = false"
      @select="onBatchSelect"
    />

    <parseHistoryDialog
      :open="historyOpen"
      @close="historyOpen = false"
      @pick="onPickHistory"
    />

    <batchParseDialog
      :open="batchParseOpen"
      :auto-add="Boolean(settingsStore.value('auto_add_to_download_list'))"
      @close="batchParseOpen = false"
      @start="onBatchParse"
    />
  </div>
</template>

<style scoped>
/* 桌面版 download_btn.setMinimumWidth(120) */
.download-btn {
  min-width: 120px;
}

.page-view {
  padding: 15px 25px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  flex: 1 1 auto;
  min-height: 0;
}

.url-box {
  display: flex;
  flex-direction: row;
  gap: 5px;
  max-height: 34px;
}

.status-bar {
  min-height: 28px;
  margin: 8px 0 2px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.status {
  color: var(--text-primary);
}

.status.error {
  color: var(--text-danger);
}

.actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 8px;
}

</style>
