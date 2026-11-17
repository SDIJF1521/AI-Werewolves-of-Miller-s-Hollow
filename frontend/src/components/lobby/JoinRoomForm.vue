<template>
  <form class="join-form" @submit.prevent="submit">
    <div class="join-form__code">
      <span class="field__label">房间号</span>
      <el-input v-model="code" maxlength="6" placeholder="例如 A7K2M" class="join-form__code-input" @input="normalize" />
    </div>
    <div class="join-form__name">
      <span class="field__label">你的代号</span>
      <el-input v-model="name" maxlength="16" placeholder="昵称" />
    </div>
    <el-button class="btn-ghost join-form__submit" native-type="submit" :loading="loading">
      加入观战 / 认领 AI
    </el-button>
  </form>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['join'])

const code = ref('')
const name = ref(localStorage.getItem('ai-werewolf-name') || '')

function normalize(value) {
  code.value = (value || '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6)
}

function submit() {
  if (!name.value.trim() || code.value.length < 4) return
  localStorage.setItem('ai-werewolf-name', name.value.trim())
  emit('join', { code: code.value.trim(), name: name.value.trim() })
}
</script>

<style scoped>
.join-form {
  display: flex;
  flex-direction: column;
  gap: 11px;
}
.field__label {
  display: block;
  margin-bottom: 6px;
  font-size: 11px;
  letter-spacing: 0.12em;
  color: var(--muted);
}
.join-form__code-input :deep(.el-input__inner) {
  font-family: var(--serif);
  font-size: 18px;
  letter-spacing: 0.24em;
  text-transform: uppercase;
}
.join-form__submit {
  width: 100%;
}
</style>
