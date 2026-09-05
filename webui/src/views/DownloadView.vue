<script setup>
import fluentLabel from "@/components/Fluent/components/widgets/label/FluentLabel.vue";
</script>

<template>
    <div class="page-view">
        <fluentLabel text="下载页面" />
        <p class="placeholder">这是一个装满了史子的下载列表。</p>
    </div>
</template>

<style scoped>
.page-view {
    padding: 15px 25px;
    display: flex;
    flex-direction: column;
    gap: 5px;
}

.placeholder {
    margin: 0;
    color: rgba(128, 128, 128, 0.9);
}
</style>