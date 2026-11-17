<template>
  <div
    class="seat"
    :class="{
      'seat--speaking': speaking,
      'seat--dead': !player.alive,
      'seat--mine': mine,
      'seat--revealed': reveal,
    }"
  >
    <span class="seat__number">{{ String(player.seat).padStart(2, '0') }}</span>
    <span v-if="mine" class="seat__mine">我的 AI</span>
    <AvatarOrb
      :avatar="player.avatar"
      :color="player.color"
      :size="46"
      :alive="player.alive"
      :speaking="speaking"
    />
    <div class="seat__info">
      <strong class="seat__name">{{ player.name }}</strong>
      <span class="seat__title">{{ reveal ? player.roleName : player.title }}</span>
    </div>
    <div class="seat__tags">
      <span v-if="wolfMate" class="seat__wolf">狼队</span>
      <span v-if="player.claim" class="seat__claim">{{ claimName(player.claim) }}</span>
      <span v-if="player.idiotRevealed" class="seat__claim seat__claim--idiot">白痴翻牌</span>
      <span v-if="voteCount" class="seat__vote">{{ voteCount }} 票</span>
      <span v-if="advisorCount" class="seat__advisors">{{ advisorCount }} 玩家</span>
      <span v-if="team?.hasKey" class="seat__key">KEY</span>
    </div>
    <span v-if="!player.alive" class="seat__death">出局</span>
  </div>
</template>

<script setup>
import AvatarOrb from '@/components/common/AvatarOrb.vue'
import { claimName } from '@/utils/game'

defineProps({
  player: { type: Object, required: true },
  team: { type: Object, default: null },
  speaking: { type: Boolean, default: false },
  mine: { type: Boolean, default: false },
  voteCount: { type: Number, default: 0 },
  reveal: { type: Boolean, default: false },
  advisorCount: { type: Number, default: 0 },
  wolfMate: { type: Boolean, default: false },
})
</script>

<style scoped>
.seat {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  width: 104px;
  padding: 8px 6px 7px;
  border-radius: 13px;
  border: 1px solid var(--line);
  background: linear-gradient(160deg, rgba(18, 25, 30, 0.92), rgba(8, 11, 13, 0.88));
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.25);
  transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.25s ease;
  backdrop-filter: blur(10px);
}
.seat--mine {
  border-color: rgba(79, 155, 130, 0.45);
}
.seat--speaking {
  border-color: rgba(216, 178, 106, 0.62);
  box-shadow: 0 0 0 1px rgba(216, 178, 106, 0.2), 0 0 26px rgba(216, 178, 106, 0.12);
  transform: translateY(-3px);
}
.seat--dead {
  opacity: 0.68;
}
.seat--revealed .seat__name {
  color: var(--gold-soft);
}
.seat__number {
  position: absolute;
  left: 7px;
  top: 5px;
  font-family: var(--serif);
  font-size: 9px;
  color: var(--muted);
  letter-spacing: 0.06em;
}
.seat__mine {
  position: absolute;
  right: 6px;
  top: 5px;
  font-size: 7px;
  letter-spacing: 0.04em;
  color: #9ed4c1;
}
.seat__info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  line-height: 1.2;
  max-width: 100%;
}
.seat__name {
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.04em;
  white-space: nowrap;
}
.seat__title {
  font-size: 8px;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 92px;
}
.seat__tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 2px;
  min-height: 14px;
}
.seat__claim,
.seat__vote,
.seat__advisors,
.seat__key,
.seat__wolf {
  font-size: 7px;
  line-height: 13px;
  padding: 0 4px;
  border-radius: 3px;
  white-space: nowrap;
}
.seat__wolf {
  color: #ffd1c9;
  background: rgba(198, 90, 79, 0.28);
  border: 1px solid rgba(198, 90, 79, 0.45);
}
.seat__claim {
  color: #e0c58f;
  background: rgba(216, 178, 106, 0.1);
  border: 1px solid rgba(216, 178, 106, 0.22);
}
.seat__claim--idiot {
  color: #cbbaf3;
  border-color: rgba(155, 123, 222, 0.25);
  background: rgba(155, 123, 222, 0.1);
}
.seat__vote {
  color: #e7a39b;
  background: rgba(198, 90, 79, 0.12);
  border: 1px solid rgba(198, 90, 79, 0.25);
}
.seat__advisors {
  color: var(--muted);
  border: 1px solid var(--line);
}
.seat__key {
  color: #9ed4c1;
  border: 1px solid rgba(79, 155, 130, 0.25);
  background: rgba(79, 155, 130, 0.08);
}
.seat__death {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  border-radius: 13px;
  background: rgba(4, 6, 7, 0.46);
  color: rgba(236, 231, 221, 0.65);
  font-family: var(--serif);
  font-size: 12px;
  letter-spacing: 0.24em;
  pointer-events: none;
}
@media (max-width: 720px) {
  .seat {
    width: 92px;
  }
}
</style>
