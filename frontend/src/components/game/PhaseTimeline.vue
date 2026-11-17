<template>
  <div class="timeline">
    <div class="timeline__day">
      <span class="serif">DAY {{ String(day).padStart(2, '0') }}</span>
      <small>{{ info.label }}</small>
    </div>
    <div class="timeline__track">
      <div
        v-for="(step, index) in steps"
        :key="step.key"
        class="timeline__step"
        :class="{
          'timeline__step--active': step.key === phase,
          'timeline__step--done': index < activeIndex,
        }"
      >
        <span class="timeline__dot"></span>
        <span class="timeline__label">{{ step.label }}</span>
        <span v-if="step.key === 'council'" class="timeline__seconds">{{ timings.council }}s</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { phaseInfo } from '@/utils/game'

const props = defineProps({
  phase: { type: String, default: 'idle' },
  day: { type: Number, default: 0 },
  timings: { type: Object, default: () => ({ council: 80 }) },
})

const steps = [
  { key: 'night_council', label: '夜谈' },
  { key: 'night', label: '夜晚' },
  { key: 'dawn', label: '天亮' },
  { key: 'council', label: '密聊' },
  { key: 'speech', label: '发言' },
  { key: 'vote_advice', label: '锁票' },
  { key: 'vote_reveal', label: '投票' },
  { key: 'last_words', label: '遗言' },
]
const info = computed(() => phaseInfo(props.phase))
const activeIndex = computed(() => {
  const index = steps.findIndex((s) => s.key === props.phase)
  if (props.phase === 'last_words') return steps.length - 1
  if (props.phase === 'special') return 5
  if (props.phase === 'finished') return steps.length
  return index < 0 ? 0 : index
})
</script>

<style scoped>
.timeline {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 9px 14px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: rgba(9, 13, 16, 0.55);
}
.timeline__day {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding-right: 16px;
  border-right: 1px solid var(--line);
  flex: none;
}
.timeline__day span {
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--gold-soft);
}
.timeline__day small {
  font-size: 8px;
  color: var(--muted);
}
.timeline__track {
  display: flex;
  align-items: center;
  gap: 4px;
  overflow-x: auto;
  min-width: 0;
  scrollbar-width: none;
}
.timeline__track::-webkit-scrollbar {
  display: none;
}
.timeline__step {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 7px;
  border-radius: 99px;
  white-space: nowrap;
  flex: none;
}
.timeline__dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(236, 231, 221, 0.18);
}
.timeline__label {
  font-size: 9px;
  color: var(--muted);
}
.timeline__seconds {
  font-size: 7px;
  color: rgba(216, 178, 106, 0.55);
}
.timeline__step--active {
  background: rgba(216, 178, 106, 0.1);
}
.timeline__step--active .timeline__dot {
  background: var(--gold);
  box-shadow: 0 0 7px var(--gold);
}
.timeline__step--active .timeline__label {
  color: var(--gold-soft);
}
.timeline__step--done .timeline__dot {
  background: rgba(79, 155, 130, 0.6);
}
.timeline__step--done .timeline__label {
  color: rgba(201, 194, 181, 0.5);
}
@media (max-width: 760px) {
  .timeline {
    gap: 10px;
    padding: 8px 10px;
  }
  .timeline__day {
    padding-right: 10px;
  }
}
</style>
