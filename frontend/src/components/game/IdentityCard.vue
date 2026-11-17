<template>
  <div v-if="team && privateInfo?.you" class="identity-strip" :class="`identity-strip--${camp}`">
    <div class="identity-strip__privacy">
      <span class="identity-strip__eye">◉</span>
      你的 AI 身份牌 · 仅你可见
    </div>
    <div class="identity-strip__main">
      <AvatarOrb :avatar="team.ai.avatar" :color="team.ai.color" :size="42" :alive="privateInfo.you.alive" />
      <div class="identity-strip__ai">
        <strong class="serif">{{ team.ai.name }}</strong>
        <span>{{ privateInfo.you.alive ? '存活' : '已出局' }} · {{ team.ai.title }}</span>
      </div>
      <span class="identity-strip__role">{{ privateInfo.you.roleName }}</span>
      <span class="identity-strip__camp">{{ privateInfo.you.camp === 'wolf' ? '狼人阵营' : '好人阵营' }}</span>
      <span class="identity-strip__ability">{{ privateInfo.you.ability }}</span>
    </div>
    <div class="identity-strip__extras">
      <div v-if="privateInfo.wolfMates?.length" class="identity-strip__mates">
        <span>狼队友</span>
        <b v-for="mate in privateInfo.wolfMates" :key="mate.seat" :class="{ dead: !mate.alive }">
          {{ mate.seat }}号 {{ mate.name }}
        </b>
      </div>
      <div v-if="privateInfo.you.checks?.length" class="identity-strip__checks">
        <span>查验</span>
        <b v-for="check in privateInfo.you.checks.slice(-3)" :key="`${check.day}-${check.target}`" :class="check.result">
          {{ check.target }}号{{ check.result === 'wolf' ? '查杀' : '金水' }}
        </b>
      </div>
      <div v-if="privateInfo.you.antidote === false || privateInfo.you.poison === false" class="identity-strip__potion">
        <span>药剂</span>
        <b v-if="privateInfo.you.antidote === false">解药已用</b>
        <b v-if="privateInfo.you.poison === false">毒药已用</b>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AvatarOrb from '@/components/common/AvatarOrb.vue'

const props = defineProps({
  team: { type: Object, default: null },
  privateInfo: { type: Object, default: null },
  game: { type: Object, default: null },
  you: { type: Object, default: null },
})

const camp = computed(() => props.privateInfo?.you?.camp || 'good')
</script>

<style scoped>
.identity-strip {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  padding: 9px 14px;
  border: 1px solid rgba(79, 155, 130, 0.25);
  border-radius: 12px;
  background:
    linear-gradient(100deg, rgba(79, 155, 130, 0.08), transparent 40%),
    rgba(9, 13, 16, 0.62);
}
.identity-strip--wolf {
  border-color: rgba(198, 90, 79, 0.35);
  background:
    linear-gradient(100deg, rgba(198, 90, 79, 0.11), transparent 42%),
    rgba(9, 13, 16, 0.62);
}
.identity-strip__privacy {
  display: flex;
  align-items: center;
  gap: 5px;
  flex: none;
  font-size: 8px;
  letter-spacing: 0.06em;
  color: var(--muted);
  padding-right: 12px;
  border-right: 1px solid var(--line);
}
.identity-strip__eye {
  color: var(--gold);
  font-size: 10px;
}
.identity-strip__main {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}
.identity-strip__ai {
  display: flex;
  flex-direction: column;
  gap: 1px;
  line-height: 1.2;
  min-width: 100px;
}
.identity-strip__ai strong {
  font-size: 14px;
  font-weight: 500;
}
.identity-strip__ai span {
  font-size: 8px;
  color: var(--muted);
}
.identity-strip__role {
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid rgba(216, 178, 106, 0.35);
  background: rgba(216, 178, 106, 0.1);
  color: var(--gold-soft);
  font-family: var(--serif);
  font-size: 11px;
}
.identity-strip--wolf .identity-strip__role {
  border-color: rgba(198, 90, 79, 0.4);
  background: rgba(198, 90, 79, 0.1);
  color: #efb1a9;
}
.identity-strip__camp {
  font-size: 8px;
  color: var(--muted);
}
.identity-strip__ability {
  flex: 1;
  min-width: 180px;
  font-size: 9px;
  line-height: 1.5;
  color: var(--text-soft);
}
.identity-strip__extras {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-left: auto;
}
.identity-strip__mates,
.identity-strip__checks,
.identity-strip__potion {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  font-size: 8px;
}
.identity-strip__mates > span,
.identity-strip__checks > span,
.identity-strip__potion > span {
  color: var(--muted);
}
.identity-strip__mates b {
  padding: 1px 5px;
  border-radius: 3px;
  background: rgba(198, 90, 79, 0.15);
  color: #f0c4be;
  font-weight: 400;
}
.identity-strip__mates b.dead {
  opacity: 0.45;
  text-decoration: line-through;
}
.identity-strip__checks b {
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: 400;
}
.identity-strip__checks b.wolf {
  color: #e7a39b;
  background: rgba(198, 90, 79, 0.1);
}
.identity-strip__checks b.good {
  color: #a8d6c4;
  background: rgba(79, 155, 130, 0.1);
}
.identity-strip__potion b {
  color: var(--muted);
  font-weight: 400;
}
@media (max-width: 900px) {
  .identity-strip__privacy {
    border-right: none;
    padding-right: 0;
    width: 100%;
  }
  .identity-strip__extras {
    margin-left: 0;
  }
  .identity-strip__ability {
    min-width: 100%;
  }
}
</style>
