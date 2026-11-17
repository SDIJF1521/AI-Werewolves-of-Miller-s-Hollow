<template>
  <div class="ring" :class="[`ring--${tone}`, { 'ring--urgent': urgent && running }]" :style="{ width: `${size}px`, height: `${size}px` }">
    <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`" class="ring__svg">
      <circle class="ring__track" :cx="center" :cy="center" :r="radius" :stroke-width="stroke" fill="none" />
      <circle
        class="ring__progress"
        :cx="center"
        :cy="center"
        :r="radius"
        :stroke-width="stroke"
        fill="none"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="offsetValue"
        stroke-linecap="round"
      />
    </svg>
    <div class="ring__content">
      <template v-if="running">
        <span class="ring__time">{{ label }}</span>
        <span v-if="sub" class="ring__sub">{{ sub }}</span>
      </template>
      <slot v-else>
        <span class="ring__time">--:--</span>
      </slot>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useCountdown } from '@/composables/useCountdown'

const props = defineProps({
  endsAt: { type: Number, default: 0 },
  total: { type: Number, default: 0 },
  offset: { type: Number, default: 0 },
  size: { type: Number, default: 112 },
  stroke: { type: Number, default: 3 },
  tone: { type: String, default: 'gold' },
  sub: { type: String, default: '' },
})

const center = computed(() => props.size / 2)
const radius = computed(() => props.size / 2 - props.stroke * 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
const { label, progress, urgent, remaining } = useCountdown(
  computed(() => props.endsAt),
  computed(() => props.total),
  computed(() => props.offset),
)
const running = computed(() => props.endsAt > 0 && remaining.value > 0)
const offsetValue = computed(() => circumference.value * (1 - progress.value))
</script>

<style scoped>
.ring {
  position: relative;
  display: inline-grid;
  place-items: center;
  flex: none;
}
.ring__svg {
  position: absolute;
  inset: 0;
  transform: rotate(-90deg);
}
.ring__track {
  stroke: rgba(236, 231, 221, 0.08);
}
.ring__progress {
  stroke: var(--gold);
  transition: stroke-dashoffset 0.25s linear, stroke 0.2s ease;
  filter: drop-shadow(0 0 5px rgba(216, 178, 106, 0.35));
}
.ring--red .ring__progress {
  stroke: var(--red);
  filter: drop-shadow(0 0 5px rgba(198, 90, 79, 0.4));
}
.ring--green .ring__progress {
  stroke: var(--green);
}
.ring--violet .ring__progress {
  stroke: var(--violet);
}
.ring--urgent .ring__progress {
  stroke: #e06a5f;
  animation: breathe 1.1s ease-in-out infinite;
}
.ring__content {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  line-height: 1.1;
}
.ring__time {
  font-family: var(--serif);
  font-size: clamp(20px, 2.4vw, 30px);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.04em;
  color: var(--text);
}
.ring--urgent .ring__time {
  color: #f1a59c;
}
.ring__sub {
  margin-top: 4px;
  font-size: 9px;
  letter-spacing: 0.16em;
  color: var(--muted);
}
</style>
