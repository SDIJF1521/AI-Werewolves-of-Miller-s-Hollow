<template>
  <span class="phase-pill" :class="`phase-pill--${info.tone}`">
    <i class="phase-pill__dot"></i>
    <span class="phase-pill__label">{{ info.label }}</span>
    <span v-if="day" class="phase-pill__day">D{{ day }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { phaseInfo } from '@/utils/game'

const props = defineProps({
  phase: { type: String, default: 'idle' },
  day: { type: Number, default: 0 },
})
const info = computed(() => phaseInfo(props.phase))
</script>

<style scoped>
.phase-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 26px;
  padding: 0 10px;
  border-radius: 99px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.02);
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--text-soft);
  white-space: nowrap;
}
.phase-pill__dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--muted);
  box-shadow: 0 0 8px currentColor;
}
.phase-pill__day {
  color: var(--muted);
  font-family: var(--serif);
}
.phase-pill--gold {
  border-color: rgba(216, 178, 106, 0.3);
  color: var(--gold-soft);
}
.phase-pill--gold .phase-pill__dot {
  background: var(--gold);
}
.phase-pill--red {
  border-color: rgba(198, 90, 79, 0.35);
  color: #e7a39b;
}
.phase-pill--red .phase-pill__dot {
  background: var(--red);
}
.phase-pill--night {
  border-color: rgba(111, 149, 187, 0.32);
  color: #b7cce0;
}
.phase-pill--night .phase-pill__dot {
  background: var(--blue);
}
.phase-pill--dawn {
  border-color: rgba(216, 178, 106, 0.22);
  color: #d9c7a3;
}
.phase-pill--dawn .phase-pill__dot {
  background: #c8a56a;
}
.phase-pill--violet {
  border-color: rgba(155, 123, 222, 0.35);
  color: #cbbaf3;
}
.phase-pill--violet .phase-pill__dot {
  background: var(--violet);
}
.phase-pill--green {
  border-color: rgba(79, 155, 130, 0.35);
  color: #a8d6c4;
}
.phase-pill--green .phase-pill__dot {
  background: var(--green);
}
</style>
