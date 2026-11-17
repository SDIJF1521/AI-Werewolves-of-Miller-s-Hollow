<template>
  <div class="voice" :class="{ 'voice--compact': compact, 'voice--active': voice.state.joined }">
    <div class="voice__head">
      <div class="voice__title">
        <span class="voice__status" :class="{ 'voice__status--live': voice.state.joined }"></span>
        <span>{{ mode === 'lobby' ? '大厅语音' : mode === 'wolf' ? '狼队语音' : '队内语音' }}</span>
        <span v-if="voice.state.joined" class="voice__latency">WebRTC · P2P</span>
      </div>
      <div class="voice__actions">
        <template v-if="voice.state.joined">
          <button class="voice__icon-btn" :class="{ 'is-muted': voice.state.muted }" type="button" @click="voice.toggleMute()">
            <el-icon><Microphone v-if="!voice.state.muted" /><Mute v-else /></el-icon>
            {{ voice.state.muted ? '已静音' : '静音' }}
          </button>
          <button class="voice__icon-btn voice__icon-btn--danger" type="button" @click="voice.leave()">离开</button>
        </template>
        <button
          v-else
          class="voice__join"
          type="button"
          :disabled="!allowed || voice.state.connecting"
          @click="voice.join()"
        >
          <el-icon><Microphone /></el-icon>
          {{ voice.state.connecting ? '连接中…' : '加入语音' }}
        </button>
      </div>
    </div>

    <div v-if="!allowed" class="voice__hint">
      {{ mode === 'wolf' ? '狼队语音只在夜间密谈开放。' : '语音只在候场、80 秒密聊和锁票阶段开放。' }}
    </div>
    <div v-else-if="voice.state.joined" class="voice__participants">
      <span class="voice__person voice__person--self" :class="{ 'is-speaking': voice.state.localSpeaking }">
        <AvatarOrb :avatar="'🎙️'" :color="'#d8b26a'" :size="24" :speaking="voice.state.localSpeaking" :muted="voice.state.muted" />
        <span>我</span>
      </span>
      <span
        v-for="(peer, id) in voice.state.peers"
        :key="id"
        class="voice__person"
        :class="{ 'is-speaking': peer.speaking }"
      >
        <AvatarOrb :avatar="peer.avatar || '🎧'" :color="'#6f95bb'" :size="24" :speaking="peer.speaking" :muted="peer.muted" />
        <span>{{ peer.name || '队友' }}</span>
        <small v-if="peer.connectionState === 'connecting'">连接中</small>
      </span>
      <span v-if="!Object.keys(voice.state.peers).length" class="voice__empty">等队友加入…</span>
    </div>
    <div v-else class="voice__hint">
      {{ mode === 'lobby'
        ? '候场大厅语音，最多 8 人同时在线。建议戴耳机。'
        : mode === 'wolf'
          ? '狼队语音只在夜间密谈开放，狼人玩家可以语音对齐刀口。'
          : '低延迟 P2P 语音。建议戴耳机，减少回声。' }}
    </div>

    <div v-if="voice.state.error" class="voice__error">{{ voice.state.error }}</div>
  </div>
</template>

<script setup>
import { Microphone, Mute } from '@element-plus/icons-vue'
import AvatarOrb from '@/components/common/AvatarOrb.vue'
import { useVoice } from '@/composables/useVoice'

defineProps({
  allowed: { type: Boolean, default: false },
  compact: { type: Boolean, default: false },
  mode: { type: String, default: 'team' },
})

const voice = useVoice()
</script>

<style scoped>
.voice {
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.16);
}
.voice--active {
  border-color: rgba(79, 155, 130, 0.25);
}
.voice__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.voice__title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11px;
  color: var(--text-soft);
  white-space: nowrap;
}
.voice__status {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--muted);
}
.voice__status--live {
  background: var(--green);
  box-shadow: 0 0 8px var(--green);
  animation: breathe 1.8s infinite;
}
.voice__latency {
  font-size: 8px;
  letter-spacing: 0.1em;
  color: var(--muted);
}
.voice__actions {
  display: flex;
  gap: 6px;
}
.voice__join,
.voice__icon-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 26px;
  padding: 0 9px;
  border-radius: 8px;
  border: 1px solid rgba(216, 178, 106, 0.3);
  background: rgba(216, 178, 106, 0.08);
  color: var(--gold-soft);
  font-size: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.voice__join:hover,
.voice__icon-btn:hover {
  background: rgba(216, 178, 106, 0.16);
}
.voice__join:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.voice__icon-btn {
  border-color: var(--line);
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-soft);
}
.voice__icon-btn.is-muted {
  color: #e7a39b;
  border-color: rgba(198, 90, 79, 0.3);
}
.voice__icon-btn--danger {
  color: #d98a82;
  border-color: rgba(198, 90, 79, 0.3);
}
.voice__hint {
  margin-top: 7px;
  font-size: 9px;
  color: var(--muted);
  line-height: 1.6;
}
.voice__participants {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.voice__person {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px 2px 3px;
  border-radius: 99px;
  border: 1px solid var(--line);
  font-size: 9px;
  color: var(--text-soft);
}
.voice__person.is-speaking {
  border-color: rgba(216, 178, 106, 0.5);
  color: var(--gold-soft);
  box-shadow: 0 0 12px rgba(216, 178, 106, 0.1);
}
.voice__person small {
  color: var(--muted);
}
.voice__person--self {
  border-color: rgba(216, 178, 106, 0.22);
}
.voice__empty {
  font-size: 9px;
  color: var(--muted);
}
.voice__error {
  margin-top: 7px;
  font-size: 9px;
  line-height: 1.5;
  color: #e7a39b;
}
</style>
