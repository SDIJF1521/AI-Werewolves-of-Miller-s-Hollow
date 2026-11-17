<template>
  <el-select
    :model-value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    clearable
    size="small"
    class="seat-picker"
    popper-class="seat-picker-popper"
    @update:model-value="onChange"
  >
    <el-option
      v-for="player in players"
      :key="player.seat"
      :label="`${player.seat} 号 · ${player.name}`"
      :value="player.seat"
      :disabled="player.seat === exclude"
    >
      <span class="seat-option">
        <span class="seat-option__num">{{ player.seat }}</span>
        <span class="seat-option__name">{{ player.name }}</span>
        <span class="seat-option__claim" v-if="player.claim">{{ claimName(player.claim) }}</span>
      </span>
    </el-option>
  </el-select>
</template>

<script setup>
import { claimName } from '@/utils/game'

const props = defineProps({
  modelValue: { type: Number, default: null },
  players: { type: Array, default: () => [] },
  exclude: { type: Number, default: null },
  placeholder: { type: String, default: '选择座位' },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

function onChange(value) {
  emit('update:modelValue', value ?? null)
}
</script>

<style scoped>
.seat-picker {
  width: 100%;
}
.seat-option {
  display: flex;
  align-items: center;
  gap: 8px;
}
.seat-option__num {
  display: inline-grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1px solid var(--line-strong);
  font-size: 11px;
  color: var(--gold-soft);
}
.seat-option__name {
  flex: 1;
}
.seat-option__claim {
  font-size: 10px;
  color: var(--muted);
}
</style>
