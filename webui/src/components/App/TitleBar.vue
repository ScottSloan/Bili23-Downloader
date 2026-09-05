<script setup></script>

<template>
  <div class="title-bar">
    <img src="/src/assets/app.svg" alt="App Icon" />
    <span>Bili23 Downloader</span>
  </div>
</template>

<style scoped>
.title-bar {
  min-height: 48px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.title-bar img {
  width: 18px;
  height: 18px;
  margin-left: 16px;
  margin-right: 12px;
}

.title-bar span {
  font-size: 10pt;
  user-select: none;
}
</style>
