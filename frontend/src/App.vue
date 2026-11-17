<template>
  <div class="app-shell">
    <div class="app-bg" aria-hidden="true">
      <div class="app-bg__glow app-bg__glow--gold"></div>
      <div class="app-bg__glow app-bg__glow--red"></div>
      <div class="app-bg__vignette"></div>
      <div class="app-bg__grain"></div>
    </div>
    <router-view v-slot="{ Component }">
      <transition name="page" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>

<script setup>
// 全局壳层：视觉背景 + 路由过渡。业务页面保持组件组合。
</script>
