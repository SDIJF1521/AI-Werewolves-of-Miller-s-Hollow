<template>
  <span v-if="feedback" class="fb" :class="[`fb--${info.tone}`, { 'fb--compact': compact }]" :title="feedback.summary || ''">
    <span class="fb__icon">{{ info.icon }}</span>
    <span class="fb__label">{{ feedback.label || info.label }}</span>
    <span v-if="!compact && feedback.detail" class="fb__detail">{{ feedback.detail }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { feedbackInfo } from '@/utils/game'

const props = defineProps({
  feedback: { type: Object, default: null },
  compact: { type: Boolean, default: false },
})
const info = computed(() => feedbackInfo(props.feedback?.kind))
</script>

<style scoped>
.fb {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  padding: 3px 9px;
  border-radius: 99px;
  border: 1px solid var(--line);
  font-size: 11px;
  color: var(--text-soft);
  background: rgba(255, 255, 255, 0.03);
  vertical-align: middle;
}
.fb__icon {
  display: inline-grid;
  place-items: center;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  font-size: 9px;
  font-weight: 700;
}
.fb__label {
  font-weight: 600;
  white-space: nowrap;
}
.fb__detail {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--muted);
  font-weight: 400;
}
.fb--full {
  border-color: rgba(79, 155, 130, 0.4);
  background: rgba(79, 155, 130, 0.1);
  color: #a8d6c4;
}
.fb--full .fb__icon {
  background: rgba(79, 155, 130, 0.25);
}
.fb--partial {
  border-color: rgba(216, 178, 106, 0.4);
  background: rgba(216, 178, 106, 0.1);
  color: var(--gold-soft);
}
.fb--partial .fb__icon {
  background: rgba(216, 178, 106, 0.22);
}
.fb--mis {
  border-color: rgba(155, 123, 222, 0.4);
  background: rgba(155, 123, 222, 0.1);
  color: #cbbaf3;
}
.fb--mis .fb__icon {
  background: rgba(155, 123, 222, 0.22);
}
.fb--defy {
  border-color: rgba(198, 90, 79, 0.42);
  background: rgba(198, 90, 79, 0.1);
  color: #e7a39b;
}
.fb--defy .fb__icon {
  background: rgba(198, 90, 79, 0.22);
}
.fb--auto {
  border-color: var(--line);
  color: var(--muted);
}
.fb--compact {
  padding: 1px 7px;
  font-size: 10px;
}
</style>
