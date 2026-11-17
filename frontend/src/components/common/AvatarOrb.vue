<template>
  <span
    class="orb"
    :class="{ 'orb--dead': !alive, 'orb--speaking': speaking, 'orb--muted': muted }"
    :style="{ width: `${size}px`, height: `${size}px`, '--orb-color': color || '#8a9b6e', fontSize: `${size * 0.42}px` }"
  >
    <span class="orb__halo"></span>
    <span class="orb__emoji">{{ avatar || '🐺' }}</span>
    <span v-if="!alive" class="orb__slash"></span>
    <span v-if="muted" class="orb__mute">×</span>
  </span>
</template>

<script setup>
defineProps({
  avatar: { type: String, default: '🐺' },
  color: { type: String, default: '#8a9b6e' },
  size: { type: Number, default: 48 },
  alive: { type: Boolean, default: true },
  speaking: { type: Boolean, default: false },
  muted: { type: Boolean, default: false },
})
</script>

<style scoped>
.orb {
  position: relative;
  display: inline-grid;
  place-items: center;
  flex: none;
  border-radius: 50%;
  background:
    radial-gradient(circle at 32% 24%, rgba(255, 255, 255, 0.18), transparent 42%),
    radial-gradient(circle at 50% 65%, color-mix(in srgb, var(--orb-color) 48%, #0c1114), #0b0f12 78%);
  border: 1px solid color-mix(in srgb, var(--orb-color) 55%, transparent);
  box-shadow: inset 0 0 18px rgba(0, 0, 0, 0.55), 0 4px 18px rgba(0, 0, 0, 0.35);
  transition: filter 0.3s ease, opacity 0.3s ease;
  user-select: none;
}
.orb__emoji {
  position: relative;
  z-index: 2;
  line-height: 1;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.4));
}
.orb__halo {
  position: absolute;
  inset: -5px;
  border-radius: 50%;
  border: 1px solid transparent;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.orb--speaking .orb__halo {
  border-color: rgba(216, 178, 106, 0.75);
  box-shadow: 0 0 0 3px rgba(216, 178, 106, 0.12), 0 0 22px rgba(216, 178, 106, 0.35);
  animation: breathe 1.4s ease-in-out infinite;
}
.orb--dead {
  filter: grayscale(1) brightness(0.55);
  opacity: 0.75;
}
.orb__slash {
  position: absolute;
  inset: 0;
  z-index: 3;
  background: linear-gradient(
    135deg,
    transparent calc(50% - 1px),
    rgba(198, 90, 79, 0.7) calc(50% - 1px),
    rgba(198, 90, 79, 0.7) calc(50% + 1px),
    transparent calc(50% + 1px)
  );
  border-radius: 50%;
}
.orb__mute {
  position: absolute;
  right: -2px;
  bottom: -2px;
  z-index: 4;
  display: grid;
  place-items: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #241211;
  border: 1px solid rgba(198, 90, 79, 0.5);
  color: #e7a39b;
  font-size: 10px;
}
</style>
