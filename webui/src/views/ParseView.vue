<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import fluentLineEdit from '@/components/Fluent/components/widgets/line_edit/LineEdit.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import transparentToolButton from '@/components/Fluent/components/widgets/button/TransparentToolButton.vue'
import parseTree from '@/components/App/parse_list/ParseTree.vue'
import searchDialog from '@/components/App/parse_list/SearchDialog.vue'
import batchSelectDialog from '@/components/App/parse_list/BatchSelectDialog.vue'
import parseHistoryDialog from '@/components/App/parse_list/ParseHistoryDialog.vue'
import downloadOptionsDialog from '@/components/App/DownloadOptionsDialog.vue'
import { useParseStore } from '@/stores/parseStore'
import { useSettingsStore } from '@/stores/settingsStore'
import { tasks as tasksApi, ApiError } from '@/api'
import { t } from '@/i18n'

const router = useRouter()
const store = useParseStore()
const settingsStore = useSettingsStore()
const url = ref('')

const dialogOpen = ref(false)
const pendingEpisodes = ref<Record<string, unknown>[]>([])
const notice = ref('')

// 工具栏那四个按钮各自的对话框。与桌面版 ParseInterface 的 toolbar_layout 一一对应
const searchOpen = ref(false)
const batchSelectOpen = ref(false)
const historyOpen = ref(false)

function onSearch({ keywords, server }: { keywords: string; server: boolean }) {
  searchOpen.value = false

  if (server) {
    void store.serverSearch(keywords)

    return
  }

  const matches = store.searchLocal(keywords)

  notice.value = keywords ? t('parse.search.matches', { count: matches }) : ''
}

function onBatchSelect(numbers: number[]) {
  batchSelectOpen.value = false

  notice.value = t('parse.batchSelect.selected', { count: store.batchSelect(numbers) })
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
 * 桌面版那边开的是一个**全局设置编辑器**（媒体设置 / 附加内容 / 下载设置三页，
 * 直接读写 config），用途是解析之前先把画质、附加内容这些调好。
 *
 * Web 端**同名的那个对话框不是一回事** —— 它带着剧集，取媒体信息再建任务。
 * 全局的那些选项在这边归设置页（画质优先级、弹幕 / 字幕 / 封面几张卡片），
 * 所以这个按钮做成跳过去的快捷方式，而不是再搭一个内容重复的对话框
 */
function openGlobalOptions() {
  void router.push('/settings')
}

async function openDownload() {
  notice.value = ''

  // 摘取走后端的 /api/parse/episodes：「树节点不算下载项」这条规则只该有一处
  const episodes = await store.checkedEpisodes()

  if (!episodes.length) {
    notice.value = t('parse.nothingChecked')

    return
  }

  pendingEpisodes.value = episodes

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
    notice.value = e instanceof ApiError ? e.message : String(e)
  }
}

function onCreated(count: number) {
  // 建出来的可能比勾选的少（重复下载、需要二次解析的会被后端拦掉），如实说
  notice.value =
    count > 0
      ? t('parse.created', { count, requested: pendingEpisodes.value.length })
      : t('parse.createdNone')

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
      <!-- 81px = 原先 content-box 下的 55px 内容宽 + 24px 内边距 + 2px 边框，
           PushButton 改用 border-box 后的等价值，渲染宽度与改动前一致 -->
      <primaryPushButton
        :title="store.loading ? t('parse.submitting') : t('parse.submit')"
        :disabled="store.loading"
        style="min-width: 81px"
        @click="submit"
      />
    </div>

    <!-- 与桌面版 toolbar_layout 同一排：左边条目计数，右边四个透明工具按钮 -->
    <div class="status-bar">
      <span v-if="store.error" class="status error">{{ store.error }}</span>
      <span v-else-if="store.mediaError" class="status error">
        {{ t('parse.mediaUnavailable', { reason: store.mediaError }) }}
      </span>
      <span v-else-if="store.total" class="status">
        {{
          t('parse.summary', {
            category: store.category,
            total: store.total,
            checked: store.checkedCount,
          })
        }}
      </span>

      <span class="flex-stretch" />

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
      <transparentToolButton
        icon="options"
        :label="t('parse.toolbar.downloadOptions')"
        @click="openGlobalOptions"
      />
    </div>

    <parseTree />

    <div v-if="store.total" class="actions">
      <span v-if="notice" class="notice">{{ notice }}</span>

      <span class="flex-stretch" />

      <pushButton
        :title="t('parse.download')"
        :disabled="!store.checkedCount"
        @click="openDownload"
      />
    </div>

    <downloadOptionsDialog
      :open="dialogOpen"
      :episodes="pendingEpisodes"
      @close="dialogOpen = false"
      @created="onCreated"
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
  </div>
</template>

<style scoped>
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
  color: var(--text-tertiary);
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

.notice {
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
