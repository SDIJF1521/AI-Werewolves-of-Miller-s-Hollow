<template>
  <div class="chat" :class="{ 'chat--compact': compact }">
    <div ref="scrollEl" class="chat__stream">
      <div v-if="!messages.length" class="chat__empty">
        <span>{{ title }}</span>
        <p>{{ emptyHint }}</p>
      </div>
      <div
        v-for="message in messages"
        :key="message.id"
        class="chat__message"
        :class="{ 'chat__message--own': message.memberId === youId, 'chat__message--system': message.system }"
      >
        <template v-if="message.system">
          <span class="chat__system">{{ message.text }}</span>
        </template>
        <template v-else>
          <div class="chat__meta">
            <strong>{{ message.name }}</strong>
            <span>{{ formatClock(message.at) }}</span>
          </div>
          <p>{{ message.text }}</p>
        </template>
      </div>
    </div>

    <div class="chat__input">
      <el-input
        v-model="draft"
        :disabled="!allowed"
        maxlength="120"
        :placeholder="allowed ? placeholder : disabledHint"
        @keydown.enter.exact.prevent="send"
      />
      <button class="chat__send" type="button" :disabled="!allowed || !draft.trim()" @click="send">
        发送
      </button>
    </div>
    <div class="chat__hint">
      <span>Enter 发送</span>
      <span>智囊团 1–3 人 · 密聊指令直达</span>
    </div>
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import { formatClock } from '@/utils/game'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  allowed: { type: Boolean, default: false },
  youId: { type: String, default: '' },
  title: { type: String, default: '密聊区' },
  emptyHint: { type: String, default: '80 秒内交换信息。不能替 AI 写发言稿，只能给策略。' },
  placeholder: { type: String, default: '给队友一个信息或判断…' },
  disabledHint: { type: String, default: '当前阶段文字密聊已关闭' },
  compact: { type: Boolean, default: false },
})
const emit = defineEmits(['send'])
const draft = ref('')
const scrollEl = ref(null)

watch(
  () => props.messages.length,
  async () => {
    await nextTick()
    if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
  },
)

function send() {
  const text = draft.value.trim()
  if (!text || !props.allowed) return
  emit('send', text)
  draft.value = ''
}
</script>

<style scoped>
.chat {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.chat__stream {
  height: 150px;
  overflow-y: auto;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.16);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.chat--compact .chat__stream {
  height: 118px;
}
.chat--compact .chat__hint {
  display: none;
}
.chat__empty {
  margin: auto;
  text-align: center;
  padding: 10px;
}
.chat__empty span {
  font-family: var(--serif);
  font-size: 13px;
  color: var(--gold-soft);
}
.chat__empty p {
  margin: 6px 0 0;
  font-size: 9px;
  line-height: 1.7;
  color: var(--muted);
}
.chat__message {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  max-width: 92%;
}
.chat__message--own {
  align-self: flex-end;
  align-items: flex-end;
}
.chat__message--system {
  align-self: center;
  max-width: 100%;
}
.chat__meta {
  display: flex;
  gap: 6px;
  align-items: baseline;
  margin-bottom: 2px;
}
.chat__meta strong {
  font-size: 9px;
  font-weight: 500;
  color: var(--gold-soft);
}
.chat__meta span {
  font-size: 7px;
  color: var(--muted);
}
.chat__message p {
  margin: 0;
  padding: 5px 9px;
  border-radius: 8px;
  border-top-left-radius: 2px;
  background: rgba(255, 255, 255, 0.045);
  font-size: 10px;
  line-height: 1.65;
  color: var(--text-soft);
  word-break: break-word;
}
.chat__message--own p {
  background: rgba(216, 178, 106, 0.13);
  color: var(--gold-soft);
  border-top-left-radius: 8px;
  border-top-right-radius: 2px;
}
.chat__system {
  display: block;
  padding: 3px 8px;
  border-radius: 99px;
  font-size: 8px;
  line-height: 1.6;
  color: var(--muted);
  background: rgba(255, 255, 255, 0.025);
  text-align: center;
}
.chat__input {
  display: flex;
  gap: 6px;
}
.chat__input :deep(.el-input__wrapper) {
  border-radius: 8px;
}
.chat__send {
  flex: none;
  width: 48px;
  border-radius: 8px;
  border: 1px solid rgba(216, 178, 106, 0.35);
  background: rgba(216, 178, 106, 0.1);
  color: var(--gold-soft);
  font-size: 10px;
  cursor: pointer;
}
.chat__send:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.chat__hint {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 7px;
  color: var(--muted);
}
</style>
