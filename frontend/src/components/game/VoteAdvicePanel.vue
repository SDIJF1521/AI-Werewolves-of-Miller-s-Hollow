<template>
  <div class="advice">
    <div class="advice__head">
      <div>
        <span class="eyebrow">LOCK THE VOTE</span>
        <h3 class="serif">最后 30 秒：投票建议</h3>
      </div>
      <span v-if="current" class="chip chip--gold">建议投 {{ current }} 号</span>
    </div>
    <p class="advice__hint">不强制。AI 会按采纳程度参考，它仍可能投别的人。</p>
    <div class="advice__grid">
      <button
        v-for="player in targets"
        :key="player.seat"
        type="button"
        class="advice__seat"
        :class="{ 'is-active': current === player.seat }"
        @click="$emit('vote', player.seat)"
      >
        <span class="advice__num">{{ player.seat }}</span>
        <span class="advice__name">{{ player.name }}</span>
        <span v-if="player.claim" class="advice__claim">{{ claimName(player.claim) }}</span>
        <span v-if="current === player.seat" class="advice__check">✓</span>
      </button>
    </div>
    <div v-if="adviceEntries.length" class="advice__weights">
      <span v-for="item in adviceEntries" :key="item.memberId">{{ item.name }} → {{ item.seat }} 号</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { claimName } from '@/utils/game'

const props = defineProps({
  players: { type: Array, default: () => [] },
  team: { type: Object, default: null },
  you: { type: Object, required: true },
})
defineEmits(['vote'])

const targets = computed(() => props.players.filter((p) => p.alive && p.seat !== props.you?.teamSeat))
const advice = computed(() => props.team?.advice || {})
const current = computed(() => {
  const values = Object.values(advice.value)
  return values[values.length - 1] || null
})
const adviceEntries = computed(() => {
  const members = props.team?.members || []
  return Object.entries(advice.value).map(([memberId, seat]) => ({
    memberId,
    seat,
    name: members.find((m) => m.id === memberId)?.name || '玩家',
  }))
})
</script>

<style scoped>
.advice {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border: 1px solid rgba(216, 178, 106, 0.25);
  border-radius: 12px;
  background: rgba(216, 178, 106, 0.035);
}
.advice__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
}
.advice__head h3 {
  margin: 5px 0 0;
  font-size: 18px;
  font-weight: 500;
}
.advice__hint {
  margin: 0;
  font-size: 9px;
  line-height: 1.6;
  color: var(--muted);
}
.advice__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
}
.advice__seat {
  position: relative;
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 7px;
  border-radius: 7px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.02);
  color: var(--text-soft);
  font-size: 9px;
  cursor: pointer;
  text-align: left;
}
.advice__seat:hover {
  border-color: var(--line-strong);
}
.advice__seat.is-active {
  border-color: rgba(216, 178, 106, 0.55);
  background: rgba(216, 178, 106, 0.1);
  color: var(--gold-soft);
}
.advice__num {
  display: grid;
  place-items: center;
  width: 17px;
  height: 17px;
  flex: none;
  border-radius: 50%;
  border: 1px solid var(--line);
  font-family: var(--serif);
  font-size: 8px;
}
.advice__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.advice__claim {
  margin-left: auto;
  font-size: 7px;
  color: var(--muted);
}
.advice__check {
  position: absolute;
  right: 3px;
  top: 2px;
  font-size: 8px;
  color: var(--green);
}
.advice__weights {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.advice__weights span {
  font-size: 8px;
  color: var(--muted);
}
</style>
