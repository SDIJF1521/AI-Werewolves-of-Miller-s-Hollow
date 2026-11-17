<template>
  <div class="feed">
    <div class="feed__head">
      <span class="eyebrow">TABLE LOG</span>
      <span>{{ feed.length }} 条动态</span>
    </div>
    <div class="feed__list">
      <div v-for="item in feed.slice(0, 8)" :key="item.id" class="feed__item" :class="`feed__item--${item.kind}`">
        <span class="feed__dot"></span>
        <span class="feed__text">{{ item.text }}</span>
        <span class="feed__time">{{ formatClock(item.at) }}</span>
      </div>
      <div v-if="!feed.length" class="feed__empty">对局动态会出现在这里。</div>
    </div>
  </div>
</template>

<script setup>
import { formatClock } from '@/utils/game'

defineProps({
  feed: { type: Array, default: () => [] },
})
</script>

<style scoped>
.feed {
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(9, 13, 16, 0.5);
}
.feed__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
}
.feed__head > span:last-child {
  font-size: 8px;
  color: var(--muted);
}
.feed__list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 150px;
  overflow-y: auto;
}
.feed__item {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: 9px;
  line-height: 1.6;
  color: var(--muted);
}
.feed__dot {
  width: 3px;
  height: 3px;
  flex: none;
  border-radius: 50%;
  background: var(--muted);
}
.feed__item--vote .feed__dot {
  background: var(--red);
}
.feed__item--skill .feed__dot {
  background: var(--violet);
}
.feed__item--system .feed__dot {
  background: var(--gold);
}
.feed__text {
  flex: 1;
  min-width: 0;
}
.feed__item--vote .feed__text {
  color: #dca29b;
}
.feed__item--skill .feed__text {
  color: #cbbaf3;
}
.feed__time {
  font-size: 7px;
  color: rgba(139, 145, 141, 0.55);
}
.feed__empty {
  font-size: 9px;
  color: var(--muted);
}
</style>
