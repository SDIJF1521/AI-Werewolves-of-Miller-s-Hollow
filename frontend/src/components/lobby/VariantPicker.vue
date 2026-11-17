<template>
  <div class="variant-picker">
    <button
      v-for="variant in variants"
      :key="variant.key"
      type="button"
      class="variant"
      :class="{ 'variant--active': variant.key === modelValue }"
      @click="$emit('update:modelValue', variant.key)"
    >
      <div class="variant__top">
        <span class="variant__count">{{ variant.playerCount }}<small>人</small></span>
        <span class="variant__check" aria-hidden="true">✓</span>
      </div>
      <strong class="variant__name serif">{{ variant.name }}</strong>
      <span class="variant__sub">{{ variant.subtitle }}</span>
      <span class="variant__tags">
        <i v-for="tag in variant.tags" :key="tag">{{ tag }}</i>
      </span>
    </button>
  </div>
</template>

<script setup>
defineProps({
  variants: { type: Array, default: () => [] },
  modelValue: { type: String, default: 'classic9' },
})
defineEmits(['update:modelValue'])
</script>

<style scoped>
.variant-picker {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.variant {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 13px 14px 12px;
  text-align: left;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.022);
  color: var(--text);
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;
}
.variant:hover {
  border-color: var(--line-strong);
  background: rgba(255, 255, 255, 0.04);
  transform: translateY(-1px);
}
.variant--active {
  border-color: rgba(216, 178, 106, 0.52);
  background: linear-gradient(150deg, rgba(216, 178, 106, 0.12), rgba(216, 178, 106, 0.02));
}
.variant__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.variant__count {
  font-family: var(--serif);
  font-size: 22px;
  color: var(--gold-soft);
  line-height: 1;
}
.variant__count small {
  margin-left: 2px;
  font-family: var(--sans);
  font-size: 10px;
  color: var(--muted);
}
.variant__check {
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 1px solid var(--line);
  font-size: 9px;
  color: transparent;
}
.variant--active .variant__check {
  border-color: var(--gold);
  background: var(--gold);
  color: #171006;
}
.variant__name {
  font-size: 14px;
  letter-spacing: 0.04em;
}
.variant__sub {
  font-size: 10px;
  color: var(--muted);
}
.variant__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 2px;
}
.variant__tags i {
  font-style: normal;
  padding: 0 6px;
  border-radius: 99px;
  border: 1px solid var(--line);
  font-size: 9px;
  color: var(--text-soft);
  line-height: 17px;
}
.variant--active .variant__tags i {
  border-color: rgba(216, 178, 106, 0.24);
  color: var(--gold-soft);
}
@media (max-width: 460px) {
  .variant-picker {
    grid-template-columns: 1fr;
  }
}
</style>
