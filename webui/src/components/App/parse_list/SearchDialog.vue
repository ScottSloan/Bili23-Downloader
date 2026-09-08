<script setup lang="ts">
/**
 * 搜索
 *
 * 对应桌面版 `gui/dialog/misc/search.py`。两种搜索，能不能选取决于当前解析结果：
 *
 * - **筛选当前页**：纯前端，在已解析出来的树里按关键词高亮
 * - **搜索全部**：把关键词写回链接重新解析。只有接口本身支持搜索的类型才有
 *   （个人空间、收藏夹、历史记录、稍后再看）—— 后端的 `extra.server_search` 说了算
 *
 * 分页内容如果接口不支持搜索（合集、每周必看），本地筛选只覆盖当前页，
 * 那时给一句提示，与桌面版同一条措辞
 */
import { computed, ref, watch } from 'vue'
import fluentDialog from '@/components/Fluent/components/dialog/FluentDialog.vue'
import lineEdit from '@/components/Fluent/components/widgets/line_edit/LineEdit.vue'
import pushButton from '@/components/Fluent/components/widgets/button/PushButton.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import { t } from '@/i18n'

const props = defineProps<{
  open: boolean
  /** 接口支持服务端搜索 */
  serverSearchAvailable: boolean
  /** 当前链接里已生效的关键词，用于回显 */
  currentKeyword: string
  /** 当前结果分页 */
  paginated: boolean
}>()

const emit = defineEmits<{
  close: []
  /** server 为 true 表示交给服务端重新解析，否则只在本地高亮 */
  search: [payload: { keywords: string; server: boolean }]
}>()

const keywords = ref('')
const server = ref(false)

watch(
  () => props.open,
  (open) => {
    if (!open) {
      return
    }

    keywords.value = props.currentKeyword

    // 已经处于服务端搜索状态时默认继续用它，便于直接改关键词 —— 与桌面版一致
    server.value = props.serverSearchAvailable && Boolean(props.currentKeyword)
  },
)

const showScope = computed(() => props.serverSearchAvailable)
const showPaginationTip = computed(() => !props.serverSearchAvailable && props.paginated)

function submit() {
  emit('search', { keywords: keywords.value.trim(), server: server.value })
}
</script>

<template>
  <fluentDialog :open="open" :title="t('parse.search.title')" width="450px" @close="emit('close')">
    <lineEdit
      v-model="keywords"
      :placeholder="t('parse.search.placeholder')"
      :aria-label="t('parse.search.title')"
      @submit="submit"
    />

    <div v-if="showScope" class="scope">
      <div class="scope-label">{{ t('parse.search.scope') }}</div>

      <label class="radio">
        <input v-model="server" type="radio" :value="false" />
        <span>{{ t('parse.search.filterPage') }}</span>
      </label>

      <label class="radio">
        <input v-model="server" type="radio" :value="true" />
        <span>{{ t('parse.search.searchAll') }}</span>
      </label>
    </div>

    <p v-if="showPaginationTip" class="tip">{{ t('parse.search.paginationTip') }}</p>

    <template #actions>
      <primaryPushButton :title="t('parse.search.confirm')" @click="submit" />
      <pushButton :title="t('settings.dialog.cancel')" @click="emit('close')" />
    </template>
  </fluentDialog>
</template>

<style scoped>
.scope {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.scope-label {
  font-size: 14px;
  color: var(--text-primary);
}

.radio {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  cursor: pointer;
}

.radio input {
  margin: 0;
  accent-color: var(--primary-color);
}

.tip {
  margin: 0;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}
</style>
