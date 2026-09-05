<script setup lang="ts">
import { ref, onMounted } from 'vue'
import fluentLineEdit from '@/components/Fluent/components/widgets/line_edit/LineEdit.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import parseTree from '@/components/App/parse_list/ParseTree.vue'
import { useParseStore } from '@/stores/parseStore'
import { t } from '@/i18n'

const store = useParseStore()
const url = ref('')

// 刷新页面后把桌面版进程里现有的解析结果拉回来，避免现场丢失
onMounted(() => store.restore())

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
      <primaryPushButton
        :title="store.loading ? t('parse.submitting') : t('parse.submit')"
        style="min-width: 55px"
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
  color: var(--tree-muted);
}

.status.error {
  color: #d9534f;
}
</style>
