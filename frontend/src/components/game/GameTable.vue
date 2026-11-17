<template>
  <div class="table" :class="{ 'table--mobile': mobile }">
    <div class="table__felt" aria-hidden="true">
      <span class="table__ring table__ring--outer"></span>
      <span class="table__ring table__ring--inner"></span>
      <span class="table__cross table__cross--h"></span>
      <span class="table__cross table__cross--v"></span>
    </div>

    <div class="table__center">
      <slot name="center" />
    </div>

    <div class="table__seats">
      <div
        v-for="(player, index) in players"
        :key="player.seat"
        class="table__seat-wrap"
        :style="seatStyle(index)"
      >
        <SeatCard
          :player="player"
          :team="teamFor(player.seat)"
          :speaking="currentSpeaker === player.seat"
          :mine="myTeamSeat === player.seat"
          :vote-count="voteCounts[player.seat] || 0"
          :reveal="reveal"
          :advisor-count="teamFor(player.seat)?.advisorCount || 0"
          :wolf-mate="wolfMates.includes(player.seat)"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import SeatCard from './SeatCard.vue'

const props = defineProps({
  players: { type: Array, default: () => [] },
  teams: { type: Array, default: () => [] },
  currentSpeaker: { type: Number, default: null },
  voteCounts: { type: Object, default: () => ({}) },
  myTeamSeat: { type: Number, default: null },
  reveal: { type: Boolean, default: false },
  wolfMates: { type: Array, default: () => [] },
})

const mobile = ref(false)
let media = null

function updateMobile() {
  mobile.value = window.innerWidth <= 860
}

onMounted(() => {
  updateMobile()
  media = window.matchMedia('(max-width: 860px)')
  media.addEventListener?.('change', updateMobile)
})
onBeforeUnmount(() => {
  media?.removeEventListener?.('change', updateMobile)
})

const players = computed(() => props.players)

function seatStyle(index) {
  if (mobile.value) return {}
  const count = players.value.length || 9
  const angle = -Math.PI / 2 + (index * 2 * Math.PI) / count
  const x = 50 + 41 * Math.cos(angle)
  const y = 50 + 40 * Math.sin(angle)
  return {
    left: `${x}%`,
    top: `${y}%`,
  }
}

function teamFor(seat) {
  return props.teams.find((t) => t.seat === seat) || null
}
</script>

<style scoped>
.table {
  position: relative;
  width: 100%;
  aspect-ratio: 1.55;
  min-height: 480px;
  max-height: 640px;
}
.table__felt {
  position: absolute;
  inset: 12% 10%;
  border-radius: 50%;
  background:
    radial-gradient(ellipse at 50% 42%, rgba(42, 63, 53, 0.42), rgba(13, 20, 18, 0.82) 62%, rgba(6, 9, 8, 0.96)),
    #0a0f0d;
  border: 1px solid rgba(216, 178, 106, 0.13);
  box-shadow:
    inset 0 0 80px rgba(0, 0, 0, 0.65),
    0 26px 70px rgba(0, 0, 0, 0.4);
}
.table__ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(216, 178, 106, 0.08);
  pointer-events: none;
}
.table__ring--outer {
  inset: 7%;
}
.table__ring--inner {
  inset: 22%;
  border-color: rgba(236, 231, 221, 0.05);
}
.table__cross {
  position: absolute;
  background: rgba(236, 231, 221, 0.035);
}
.table__cross--h {
  left: 16%;
  right: 16%;
  top: 50%;
  height: 1px;
}
.table__cross--v {
  top: 16%;
  bottom: 16%;
  left: 50%;
  width: 1px;
}
.table__center {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
  width: 190px;
  display: flex;
  justify-content: center;
}
.table__seats {
  position: absolute;
  inset: 0;
  z-index: 3;
}
.table__seat-wrap {
  position: absolute;
  transform: translate(-50%, -50%);
  transition: left 0.3s ease, top 0.3s ease;
}

.table--mobile {
  aspect-ratio: auto;
  min-height: 0;
  max-height: none;
  padding: 10px;
}
.table--mobile .table__felt {
  inset: 0;
  border-radius: 18px;
}
.table--mobile .table__center {
  position: relative;
  left: auto;
  top: auto;
  transform: none;
  width: 100%;
  margin-bottom: 14px;
}
.table--mobile .table__seats {
  position: relative;
  inset: auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  justify-items: center;
}
.table--mobile .table__seat-wrap {
  position: static;
  transform: none;
}
@media (max-width: 1100px) {
  .table {
    min-height: 440px;
  }
  .table__center {
    width: 160px;
  }
}
</style>
