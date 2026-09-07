<script setup lang="ts">
import { ref } from 'vue'
import fluentLineEdit from '@/components/Fluent/components/widgets/line_edit/LineEdit.vue'
import primaryPushButton from '@/components/Fluent/components/widgets/button/PrimaryPushButton.vue'
import parseTree from '@/components/App/parse_list/ParseTree.vue'
import { useParseStore } from '@/stores/parseStore'
import { t } from '@/i18n'

const store = useParseStore()
const url = ref('')

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
</style>
