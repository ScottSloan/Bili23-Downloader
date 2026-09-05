<script setup lang="ts">
import { computed } from 'vue'
import { useParseStore, CHECKED, PARTIAL } from '@/stores/parseStore'
import { cellText } from './formatters'
import type { CheckState, ParseNode } from '@/api/types'
import { t, columnName } from '@/i18n'

const store = useParseStore()

// 用 CSS grid 列宽复刻 GUI 的列配置：标题列吃掉剩余空间，其余按配置的像素宽度
const gridTemplate = computed(() =>
  store.visibleColumns
    .map((column) => (column.key === 'title' ? 'minmax(0, 1fr)' : `${column.width}px`))
    .join(' '),
)

function stateOf(id: string): CheckState {
  return store.checkState.get(id) ?? 0
}

function onToggle(node: ParseNode, event: Event) {
  store.setChecked(node.id, (event.target as HTMLInputElement).checked)
}
</script>

<template>
  <div class="parse-tree">
    <div class="tree-header" :style="{ gridTemplateColumns: gridTemplate }">
      <div v-for="column in store.visibleColumns" :key="column.key" class="header-cell">
        {{ columnName(column.key) }}
      </div>
    </div>

    <div class="tree-body">
      <div
        v-for="{ node, depth } in store.rows"
        :key="node.id"
        class="tree-row"
        :class="{ 'is-node': node.is_node, 'is-reparse': node.needs_reparse }"
        :style="{ gridTemplateColumns: gridTemplate }"
      >
        <div
          v-for="(column, index) in store.visibleColumns"
          :key="column.key"
          class="body-cell"
          :style="index === 0 ? { paddingLeft: `${depth * 20 + 8}px` } : null"
        >
          <template v-if="index === 0">
            <span
              class="chevron"
              :class="{ open: store.expanded.has(node.id), hidden: !node.children }"
              @click="store.toggleExpanded(node.id)"
            >
              &#9656;
            </span>

            <input
              type="checkbox"
              class="row-check"
              :checked="stateOf(node.id) === CHECKED"
              :indeterminate="stateOf(node.id) === PARTIAL"
              @change="onToggle(node, $event)"
            />
          </template>

          <span class="cell-text" :title="cellText(node, column.key)">
            {{ cellText(node, column.key) }}
          </span>

          <span v-if="index === 1 && node.already_downloaded" class="tag">{{
            t('parse.tagDownloaded')
          }}</span>
          <span v-if="index === 1 && node.needs_reparse" class="tag">{{
            t('parse.tagNeedsReparse')
          }}</span>
        </div>
      </div>

      <p v-if="!store.rows.length" class="empty">{{ t('parse.empty') }}</p>
    </div>
  </div>
</template>

<style scoped>
.parse-tree {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
}

.tree-header,
.tree-row {
  display: grid;
  align-items: center;
  column-gap: 8px;
}

.tree-header {
  padding: 6px 4px;
  font-size: 10pt;
  border-bottom: 1px solid var(--divider-stroke);
  color: var(--text-tertiary);
  user-select: none;
}

.tree-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
}

.tree-row {
  padding: 5px 4px;
  border-radius: 4px;
  user-select: none;
}

.tree-row:hover {
  background-color: var(--subtle-fill-secondary);
}

.tree-row.is-node {
  font-weight: 600;
}

.tree-row.is-reparse .cell-text {
  color: var(--text-tertiary);
}

.header-cell,
.body-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.cell-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chevron {
  flex: 0 0 auto;
  width: 14px;
  text-align: center;
  cursor: pointer;
  transition: transform 0.15s ease;
  color: var(--text-tertiary);
}

.chevron.open {
  transform: rotate(90deg);
}

.chevron.hidden {
  visibility: hidden;
  cursor: default;
}

.row-check {
  flex: 0 0 auto;
  margin: 0;
  accent-color: var(--primary-color);
}

.tag {
  flex: 0 0 auto;
  font-size: 8pt;
  padding: 1px 5px;
  border-radius: 3px;
  color: var(--text-tertiary);
  border: 1px solid var(--divider-stroke);
}

.empty {
  color: var(--text-tertiary);
  padding: 12px 4px;
}
</style>
