<script setup lang="ts">
import pushButton from './PushButton.vue'

withDefaults(
  defineProps<{
    /** 按钮文字 */
    title: string
    /** 禁用态，透传给 PushButton 的原生 disabled */
    disabled?: boolean
    /** 原生 button 的 type，表单里的提交按钮要传 'submit' */
    type?: 'button' | 'submit' | 'reset'
  }>(),
  {
    disabled: false,
    type: 'button',
  },
)
</script>

<template>
  <!--
    primary 的样式在 PushButton 内部按 variant 分支，不放在这里：
    scoped 样式命中子组件根元素靠的是「父作用域 id 会打到子组件根节点上」这条规则，
    PushButton 一旦改成多根节点就会静默失效
  -->
  <pushButton :title="title" :disabled="disabled" :type="type" variant="primary" />
</template>
