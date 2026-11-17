<template>
  <div class="logo" :class="{ 'logo--compact': compact }">
    <span class="logo__mark" aria-hidden="true">
      <span class="logo__mark-inner">幕</span>
    </span>
    <span v-if="!compact" class="logo__text">
      <strong class="serif">AI 狼人杀</strong>
      <small>幕后智囊团</small>
    </span>
    <span v-else class="logo__compact-text serif">幕后</span>
  </div>
</template>

<script setup>
defineProps({
  compact: { type: Boolean, default: false },
})
</script>

<style scoped>
.logo {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  user-select: none;
}
.logo__mark {
  position: relative;
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border: 1px solid rgba(216, 178, 106, 0.55);
  transform: rotate(45deg);
  background: linear-gradient(135deg, rgba(216, 178, 106, 0.14), rgba(0, 0, 0, 0.2));
  box-shadow: inset 0 0 18px rgba(216, 178, 106, 0.12), 0 0 24px rgba(216, 178, 106, 0.08);
}
.logo__mark::before {
  content: '';
  position: absolute;
  inset: 5px;
  border: 1px solid rgba(216, 178, 106, 0.18);
}
.logo__mark-inner {
  transform: rotate(-45deg);
  font-family: var(--serif);
  font-size: 20px;
  color: var(--gold-soft);
}
.logo__text {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}
.logo__text strong {
  font-size: 18px;
  letter-spacing: 0.14em;
  font-weight: 600;
}
.logo__text small {
  margin-top: 4px;
  font-size: 9px;
  letter-spacing: 0.38em;
  color: var(--muted);
}
.logo--compact .logo__mark {
  width: 32px;
  height: 32px;
}
.logo--compact .logo__mark-inner {
  font-size: 15px;
}
.logo__compact-text {
  font-size: 14px;
  letter-spacing: 0.14em;
  color: var(--gold-soft);
}
</style>
