<template>
  <form class="create-form" @submit.prevent="submit">
    <div class="field-row">
      <label class="field">
        <span class="field__label">你的代号</span>
        <el-input v-model="name" maxlength="16" placeholder="玩家昵称" />
      </label>
      <label class="field">
        <span class="field__label">牌局名</span>
        <el-input v-model="roomName" maxlength="24" placeholder="例如：午夜十二人局" />
      </label>
    </div>

    <div class="field">
      <span class="field__label">选择板子</span>
      <VariantPicker v-model="variantKey" :variants="variants" />
    </div>

    <div class="field">
      <span class="field__label">对局模式</span>
      <div class="timing">
        <button
          type="button"
          class="timing__item"
          :class="{ 'timing__item--active': mode === 'practice' }"
          @click="mode = 'practice'"
        >
          <strong>训练局 · AI 补位</strong>
          <small>1 人也能开，完整跑完一局</small>
        </button>
        <button
          type="button"
          class="timing__item"
          :class="{ 'timing__item--active': mode === 'multiplayer' }"
          @click="mode = 'multiplayer'"
        >
          <strong>标准局 · 至少 9 人</strong>
          <small>一人控制一个 AI</small>
        </button>
      </div>
    </div>

    <div class="field">
      <span class="field__label">节奏</span>
      <div class="timing">
        <button
          v-for="item in timings"
          :key="item.value"
          type="button"
          class="timing__item"
          :class="{ 'timing__item--active': timing === item.value }"
          @click="timing = item.value"
        >
          <strong>{{ item.label }}</strong>
          <small>{{ item.hint }}</small>
        </button>
      </div>
    </div>

    <el-button class="btn-gold create-form__submit" native-type="submit" :loading="loading" size="large">
      创建牌局，召集幕后玩家
    </el-button>
    <p class="create-form__note">
      {{ mode === 'practice'
        ? '训练局会由 AI 自动补位，1 人即可开完整对局；适合先熟悉流程或单人体验。'
        : '标准局一人一个 AI，至少 9 名真人才能开局；12 人板允许 9–12 人，剩余 AI 自主行动。' }}
    </p>
  </form>
</template>

<script setup>
import { ref } from 'vue'
import VariantPicker from './VariantPicker.vue'

defineProps({
  variants: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['submit'])

const savedName = localStorage.getItem('ai-werewolf-name') || ''
const name = ref(savedName)
const roomName = ref('')
const variantKey = ref('classic9')
const timing = ref('standard')
const mode = ref('practice')
const timings = [
  { value: 'standard', label: '标准局', hint: '80 秒密聊 · 60 秒发言' },
  { value: 'fast', label: '快速局', hint: '12 秒密聊 · 演示友好' },
]

function submit() {
  if (!name.value.trim()) return
  localStorage.setItem('ai-werewolf-name', name.value.trim())
  emit('submit', {
    name: name.value.trim(),
    roomName: roomName.value.trim(),
    variantKey: variantKey.value,
    timing: timing.value,
    mode: mode.value,
  })
}
</script>

<style scoped>
.create-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}
.field__label {
  font-size: 11px;
  letter-spacing: 0.12em;
  color: var(--muted);
}
.timing {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.timing__item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 3px;
  padding: 10px 12px;
  border-radius: 11px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.02);
  color: var(--text-soft);
  cursor: pointer;
  text-align: left;
}
.timing__item strong {
  font-size: 12px;
}
.timing__item small {
  font-size: 9px;
  color: var(--muted);
}
.timing__item--active {
  border-color: rgba(216, 178, 106, 0.45);
  background: rgba(216, 178, 106, 0.08);
  color: var(--gold-soft);
}
.create-form__submit {
  width: 100%;
  margin-top: 2px;
}
.create-form__note {
  margin: -4px 0 0;
  font-size: 10px;
  line-height: 1.7;
  color: var(--muted);
}
@media (max-width: 560px) {
  .field-row {
    grid-template-columns: 1fr;
  }
}
</style>
