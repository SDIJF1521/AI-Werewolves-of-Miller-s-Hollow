<template>
  <button
    type="button"
    class="team-card"
    :class="{
      'team-card--selected': selected,
      'team-card--mine': mine,
      'team-card--full': team.advisorCount >= 3,
    }"
    @click="$emit('select', team.seat)"
  >
    <div class="team-card__head">
      <span class="team-card__seat">{{ String(team.seat).padStart(2, '0') }}</span>
      <span class="team-card__badges">
        <span v-if="team.hasKey" class="team-card__key" title="已配置 AI Key">KEY</span>
        <span v-if="mine" class="team-card__mine">我</span>
      </span>
    </div>
    <div class="team-card__ai">
      <AvatarOrb :avatar="team.ai.avatar" :color="team.ai.color" :size="50" />
      <div class="team-card__name">
        <strong class="serif">{{ team.ai.name }}</strong>
        <span>{{ team.ai.title }}</span>
      </div>
    </div>
    <div class="team-card__slots">
      <span
        v-for="index in 3"
        :key="index"
        class="team-card__slot"
        :class="{ 'is-filled': team.members[index - 1] }"
      >
        <template v-if="team.members[index - 1]">
          {{ team.members[index - 1].name }}
          <i v-if="team.members[index - 1].hasKey">KEY</i>
        </template>
        <template v-else>等待玩家</template>
      </span>
    </div>
    <div class="team-card__foot">
      <span>{{ team.advisorCount }}/3 玩家</span>
      <span v-if="team.advisorCount >= 3" class="team-card__captain">已满</span>
      <span v-else-if="team.advisorCount" class="team-card__captain">可加入</span>
      <span v-else class="muted">空缺</span>
    </div>
  </button>
</template>

<script setup>
import AvatarOrb from '@/components/common/AvatarOrb.vue'

defineProps({
  team: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  mine: { type: Boolean, default: false },
})
defineEmits(['select'])
</script>

<style scoped>
.team-card {
  display: flex;
  flex-direction: column;
  gap: 11px;
  padding: 13px;
  text-align: left;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.018);
  color: var(--text);
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;
}
.team-card:hover {
  border-color: var(--line-strong);
  background: rgba(255, 255, 255, 0.035);
  transform: translateY(-2px);
}
.team-card--selected {
  border-color: rgba(216, 178, 106, 0.55);
  background: linear-gradient(160deg, rgba(216, 178, 106, 0.1), rgba(216, 178, 106, 0.02));
}
.team-card--mine {
  border-color: rgba(79, 155, 130, 0.4);
}
.team-card--mine.team-card--selected {
  border-color: rgba(216, 178, 106, 0.65);
}
.team-card--full:not(.team-card--mine) {
  opacity: 0.62;
}
.team-card__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.team-card__seat {
  font-family: var(--serif);
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--muted);
}
.team-card__badges {
  display: flex;
  gap: 4px;
}
.team-card__key {
  padding: 0 5px;
  border-radius: 3px;
  background: rgba(216, 178, 106, 0.18);
  color: var(--gold-soft);
  font-size: 8px;
  letter-spacing: 0.06em;
  line-height: 15px;
}
.team-card__mine {
  padding: 0 5px;
  border-radius: 3px;
  background: rgba(79, 155, 130, 0.18);
  color: #a8d6c4;
  font-size: 8px;
  line-height: 15px;
}
.team-card__ai {
  display: flex;
  align-items: center;
  gap: 10px;
}
.team-card__name {
  display: flex;
  flex-direction: column;
  gap: 1px;
  line-height: 1.2;
}
.team-card__name strong {
  font-size: 17px;
  font-weight: 500;
  letter-spacing: 0.04em;
}
.team-card__name span {
  font-size: 9px;
  color: var(--muted);
}
.team-card__slots {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.team-card__slot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 18px;
  padding: 0 6px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.14);
  font-size: 9px;
  color: var(--muted);
}
.team-card__slot.is-filled {
  color: var(--text-soft);
  background: rgba(255, 255, 255, 0.035);
}
.team-card__slot i {
  font-style: normal;
  font-size: 8px;
  color: var(--gold);
}
.team-card__foot {
  display: flex;
  justify-content: space-between;
  font-size: 8px;
  color: var(--muted);
  padding-top: 7px;
  border-top: 1px solid var(--line);
}
.team-card__captain {
  color: var(--gold);
}
</style>
