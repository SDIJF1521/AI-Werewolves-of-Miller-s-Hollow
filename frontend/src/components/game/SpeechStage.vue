<template>
  <div class="speech-stage" :class="{ 'speech-stage--thinking': thinking, 'speech-stage--empty': !speech && !thinking }">
    <template v-if="thinking && (!speech || thinking.seat !== speech.seat)">
      <div class="speech-stage__avatar">
        <AvatarOrb :avatar="thinkingAvatar" :color="'#8a9b6e'" :size="42" :speaking="true" />
      </div>
      <div class="speech-stage__body">
        <div class="speech-stage__meta">
          <strong>{{ thinking.name }}</strong>
          <span class="speech-stage__status">正在组织语言<span class="dots"></span></span>
        </div>
        <div class="speech-stage__skeleton">
          <i></i><i></i><i></i>
        </div>
      </div>
    </template>

    <template v-else-if="speech">
      <div class="speech-stage__avatar">
        <AvatarOrb :avatar="speaker?.avatar || '🐺'" :color="speaker?.color" :size="46" :speaking="true" />
      </div>
      <div class="speech-stage__body" @click="typewriter.skip()">
        <div class="speech-stage__meta">
          <span class="speech-stage__seat">{{ speech.seat }} 号</span>
          <strong>{{ speaker?.name || speech.name || 'AI' }}</strong>
          <span v-if="speech.claim" class="chip chip--gold">{{ claimName(speech.claim) }}</span>
          <span v-if="isLastWords" class="chip chip--red">遗言</span>
          <FeedbackBadge v-if="speech.feedback" :feedback="publicFeedback" compact />
          <button type="button" class="speech-stage__replay" @click.stop="$emit('replay')">重听</button>
          <span class="speech-stage__phase">{{ isLastWords ? 'LAST WORDS' : 'SPEECH' }}</span>
        </div>
        <p class="speech-stage__text">
          {{ typewriter.display.value }}
          <span v-if="!typewriter.done.value" class="speech-stage__cursor">▍</span>
        </p>
        <div v-if="isMine && speech.feedback?.detail" class="speech-stage__feedback">
          <span class="speech-stage__feedback-label">对玩家说</span>
          {{ speech.feedback.detail }}
        </div>
        <div class="speech-stage__foot">
          <span v-if="speech.voteIntent">意向投票：{{ speech.voteIntent }} 号</span>
          <span v-if="!typewriter.done.value" class="muted">点击文字可跳过打字</span>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="speech-stage__idle-mark">◈</div>
      <div class="speech-stage__body">
        <div class="speech-stage__meta">
          <strong>{{ info.label }}</strong>
          <span class="speech-stage__phase">{{ info.hint }}</span>
        </div>
        <p class="speech-stage__text speech-stage__text--muted">
          {{ latestLog }}
        </p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AvatarOrb from '@/components/common/AvatarOrb.vue'
import FeedbackBadge from './FeedbackBadge.vue'
import { useTypewriter } from '@/composables/useTypewriter'
import { claimName, phaseInfo } from '@/utils/game'

const props = defineProps({
  game: { type: Object, default: null },
  latestSpeech: { type: Object, default: null },
  thinking: { type: Object, default: null },
  lastWords: { type: Object, default: null },
  teamSeat: { type: Number, default: null },
})
defineEmits(['replay'])

const info = computed(() => phaseInfo(props.game?.phase))
const isLastWords = computed(() => Boolean(props.lastWords))
const speech = computed(() => {
  if (props.lastWords) return { ...props.lastWords, feedback: null, claim: null }
  const phase = props.game?.phase
  if (!['speech', 'vote_reveal', 'last_words'].includes(phase)) return null
  if (props.latestSpeech) return props.latestSpeech
  const list = props.game?.speeches || []
  return list[list.length - 1] || null
})
const speaker = computed(() => {
  const seat = speech.value?.seat
  if (!seat) return null
  return props.game?.players?.find((p) => p.seat === seat) || null
})
const thinkingAvatar = computed(() => {
  const player = props.game?.players?.find((p) => p.seat === props.thinking?.seat)
  return player?.avatar || '🐺'
})
const isMine = computed(() => Boolean(speech.value?.seat && speech.value.seat === props.teamSeat))
const publicFeedback = computed(() => {
  const feedback = speech.value?.feedback
  if (!feedback) return null
  if (isMine.value) return feedback
  return { kind: feedback.kind, label: feedback.label }
})
const latestLog = computed(() => {
  const logs = props.game?.logs || []
  return logs[logs.length - 1]?.text || '等待下一步。'
})

const text = computed(() => speech.value?.text || '')
const typewriter = useTypewriter(text, 18)
</script>

<style scoped>
.speech-stage {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  min-height: 112px;
  padding: 15px 18px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background:
    linear-gradient(120deg, rgba(216, 178, 106, 0.04), transparent 40%),
    rgba(12, 17, 21, 0.82);
  box-shadow: 0 18px 46px rgba(0, 0, 0, 0.24);
}
.speech-stage--thinking {
  border-color: rgba(216, 178, 106, 0.2);
}
.speech-stage--empty {
  background: rgba(10, 14, 17, 0.56);
}
.speech-stage__avatar {
  flex: none;
  padding-top: 2px;
}
.speech-stage__body {
  flex: 1;
  min-width: 0;
  cursor: default;
}
.speech-stage__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
  min-height: 20px;
}
.speech-stage__seat {
  font-family: var(--serif);
  font-size: 9px;
  letter-spacing: 0.1em;
  color: var(--gold);
}
.speech-stage__meta strong {
  font-family: var(--serif);
  font-size: 15px;
  font-weight: 500;
  letter-spacing: 0.04em;
}
.speech-stage__phase {
  margin-left: auto;
  font-size: 8px;
  letter-spacing: 0.2em;
  color: var(--muted);
}
.speech-stage__replay {
  height: 19px;
  padding: 0 6px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.02);
  color: var(--muted);
  font-size: 8px;
  cursor: pointer;
}
.speech-stage__replay:hover {
  border-color: rgba(216, 178, 106, 0.35);
  color: var(--gold-soft);
}
.speech-stage__status {
  font-size: 10px;
  color: var(--gold-soft);
}
.dots::after {
  content: '...';
  animation: dots 1.4s steps(1) infinite;
}
.speech-stage__text {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.9;
  color: var(--text);
  word-break: break-word;
  cursor: pointer;
}
.speech-stage__text--muted {
  color: var(--muted);
  font-size: 11px;
}
.speech-stage__cursor {
  color: var(--gold);
  animation: breathe 0.8s infinite;
}
.speech-stage__feedback {
  margin-top: 9px;
  padding: 7px 10px;
  border-left: 2px solid rgba(216, 178, 106, 0.5);
  background: rgba(216, 178, 106, 0.04);
  font-size: 10px;
  line-height: 1.6;
  color: var(--text-soft);
}
.speech-stage__feedback-label {
  display: inline-block;
  margin-right: 6px;
  font-size: 8px;
  letter-spacing: 0.12em;
  color: var(--gold);
}
.speech-stage__foot {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 7px;
  font-size: 8px;
  color: var(--muted);
}
.speech-stage__skeleton {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-top: 10px;
}
.speech-stage__skeleton i {
  height: 8px;
  border-radius: 4px;
  background: linear-gradient(90deg, rgba(216, 178, 106, 0.06), rgba(216, 178, 106, 0.16), rgba(216, 178, 106, 0.06));
  background-size: 200% 100%;
  animation: shimmer 1.6s linear infinite;
}
.speech-stage__skeleton i:nth-child(1) {
  width: 88%;
}
.speech-stage__skeleton i:nth-child(2) {
  width: 72%;
}
.speech-stage__skeleton i:nth-child(3) {
  width: 54%;
}
.speech-stage__idle-mark {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  flex: none;
  border: 1px solid var(--line);
  border-radius: 50%;
  color: var(--gold);
  font-size: 16px;
}
@keyframes shimmer {
  to {
    background-position: -200% 0;
  }
}
@media (max-width: 680px) {
  .speech-stage {
    padding: 12px;
  }
  .speech-stage__text {
    font-size: 12px;
  }
  .speech-stage__phase {
    display: none;
  }
}
</style>
