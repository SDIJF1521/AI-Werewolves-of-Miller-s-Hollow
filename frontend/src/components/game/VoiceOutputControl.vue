<template>
  <el-popover placement="bottom-end" :width="260" trigger="hover" popper-class="voice-output-popper">
    <template #reference>
      <button
        type="button"
        class="voice-output"
        :class="{ 'is-on': speech.state.enabled, 'is-speaking': speech.state.speaking }"
        :disabled="!speech.state.supported"
        :title="speech.state.supported ? 'AI 发言按人格音色朗读' : '当前浏览器不支持语音合成'"
        @click="speech.toggle()"
      >
        <el-icon><Headset /></el-icon>
        <span>{{ speech.state.supported ? (speech.state.enabled ? 'AI 语音' : '语音关') : '无语音' }}</span>
        <i v-if="speech.state.speaking" class="voice-output__wave"></i>
      </button>
    </template>
    <div class="voice-output__panel">
      <div class="voice-output__title">
        <span>AI 语音输出</span>
        <span class="chip" :class="{ 'chip--green': speech.state.enabled }">{{ speech.state.enabled ? '开启' : '关闭' }}</span>
      </div>
      <p>每个 AI 使用不同的音高、语速和音色匹配性格。例如沈砚低沉克制，唐糖偏高偏快，迟野更慢。</p>
      <div class="voice-output__meta">
        <span>当前音色</span>
        <strong>{{ speech.state.voiceName || '播放时自动选择' }}</strong>
      </div>
      <div class="voice-output__actions">
        <el-button class="btn-ghost" size="small" @click="speech.test()">试听沈砚</el-button>
        <el-button class="btn-ghost" size="small" @click="speech.stop()">停止</el-button>
      </div>
      <p v-if="speech.state.error" class="voice-output__error">{{ speech.state.error }}</p>
      <p class="voice-output__note">使用浏览器 Web Speech API，不会上传文本；中文音色取决于操作系统与浏览器。</p>
    </div>
  </el-popover>
</template>

<script setup>
import { Headset } from '@element-plus/icons-vue'
import { useSpeech } from '@/composables/useSpeech'

const speech = useSpeech()
</script>

<style scoped>
.voice-output {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 27px;
  padding: 0 9px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.02);
  color: var(--muted);
  font-size: 9px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.voice-output:hover {
  border-color: var(--line-strong);
  color: var(--text-soft);
}
.voice-output.is-on {
  border-color: rgba(79, 155, 130, 0.35);
  color: #a8d6c4;
  background: rgba(79, 155, 130, 0.07);
}
.voice-output.is-speaking {
  border-color: rgba(216, 178, 106, 0.55);
  color: var(--gold-soft);
  box-shadow: 0 0 15px rgba(216, 178, 106, 0.12);
}
.voice-output:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.voice-output__wave {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--gold);
  animation: breathe 0.8s infinite;
}
.voice-output__panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.voice-output__title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: var(--text);
}
.voice-output__panel p {
  margin: 0;
  font-size: 9px;
  line-height: 1.7;
  color: var(--muted);
}
.voice-output__meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.03);
}
.voice-output__meta span {
  font-size: 8px;
  color: var(--muted);
}
.voice-output__meta strong {
  font-size: 9px;
  font-weight: 500;
  color: var(--text-soft);
}
.voice-output__actions {
  display: flex;
  gap: 5px;
}
.voice-output__error {
  color: #e7a39b !important;
}
.voice-output__note {
  font-size: 8px !important;
  opacity: 0.75;
}
@media (max-width: 560px) {
  .voice-output {
    padding: 0 6px;
  }
  .voice-output span {
    display: none;
  }
}
</style>
