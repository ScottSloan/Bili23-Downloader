<script setup lang="ts">
import pushButton from './PushButton.vue'

defineProps({
  title: {
    type: String,
    required: true,
  },
})
</script>

<template>
  <!--
    primary 的样式在 PushButton 内部按 variant 分支，不放在这里：
    scoped 样式命中子组件根元素靠的是「父作用域 id 会打到子组件根节点上」这条规则，
    PushButton 一旦改成多根节点就会静默失效
  -->
  <pushButton :title="title" variant="primary" />
</template>
