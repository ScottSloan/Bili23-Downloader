<script setup lang="ts">
import { ref } from 'vue'
import fluentLineEdit from '@/components/Fluent/components/widgets/line_edit/LineEdit.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import parseTree from '@/components/App/parse_list/ParseTree.vue'
import downloadOptionsDialog from '@/components/App/DownloadOptionsDialog.vue'
import { useParseStore } from '@/stores/parseStore'
import { t } from '@/i18n'

const store = useParseStore()
const url = ref('')

const dialogOpen = ref(false)
const pendingEpisodes = ref<Record<string, unknown>[]>([])
const notice = ref('')

async function openDownload() {
  notice.value = ''

  // 摘取走后端的 /api/parse/episodes：「树节点不算下载项」这条规则只该有一处
  const episodes = await store.checkedEpisodes()

  if (!episodes.length) {
    notice.value = t('parse.nothingChecked')

    return
  }

  pendingEpisodes.value = episodes
  dialogOpen.value = true
}

function onCreated(count: number) {
  // 建出来的可能比勾选的少（重复下载、需要二次解析的会被后端拦掉），如实说
  notice.value =
    count > 0
      ? t('parse.created', { count, requested: pendingEpisodes.value.length })
      : t('parse.createdNone')
}

// 新后端没有「取回上次解析结果」的接口 —— 那是 S0 垫片专有的。
// 解析结果只活在这个页面里，刷新即清空

function submit() {
  store.parse(url.value)
}
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
  min-height: 20px;
  margin: 8px 0 2px;
  font-size: 10pt;
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
