import { reactive } from 'vue'
import { voiceProfileFor } from '@/utils/personaVoice'

const ENABLED_KEY = 'ai-werewolf-voice-enabled'

const supported =
  typeof window !== 'undefined' &&
  'speechSynthesis' in window &&
  'SpeechSynthesisUtterance' in window

const state = reactive({
  supported,
  enabled: supported && localStorage.getItem(ENABLED_KEY) !== '0',
  speaking: false,
  seat: null,
  name: '',
  voiceName: '',
  error: '',
})

let voices = []
let current = null
let voicesBound = false

function loadVoices() {
  if (!supported) return
  voices = window.speechSynthesis.getVoices() || []
  if (!state.voiceName && voices.length) {
    const zh = voices.find((v) => /^zh/i.test(v.lang))
    state.voiceName = zh?.name || voices[0]?.name || ''
  }
}

function bindVoices() {
  if (voicesBound || !supported) return
  voicesBound = true
  loadVoices()
  window.speechSynthesis.addEventListener?.('voiceschanged', loadVoices)
}

function pickVoice(profile) {
  bindVoices()
  loadVoices()
  if (!voices.length) return null
  const chinese = voices.filter((v) => /^zh/i.test(v.lang) || /cmn|Chinese|中文|普通话/i.test(v.name))
  const pool = chinese.length ? chinese : voices
  const hints = profile.hints || []
  for (const hint of hints) {
    const hit = pool.find((v) => v.name.toLowerCase().includes(hint.toLowerCase()))
    if (hit) return hit
  }
  return pool[0] || null
}

function cleanForSpeech(text) {
  return String(text || '')
    .replace(/```[\s\S]*?```/g, '')
    .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, '')
    .replace(/[*_#>`~]/g, '')
    .replace(/……|…/g, '，')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 560)
}

function finish() {
  state.speaking = false
  state.seat = null
  state.name = ''
  current = null
}

export function useSpeech() {
  function speak({ text, name = '', seat = null, force = false } = {}) {
    if (!supported) {
      state.error = '当前浏览器不支持语音合成，请换 Chrome / Edge 试试'
      return false
    }
    if (!state.enabled && !force) return false
    if (force && !state.enabled) {
      state.enabled = true
      localStorage.setItem(ENABLED_KEY, '1')
    }
    const clean = cleanForSpeech(text)
    if (!clean) return false

    bindVoices()
    window.speechSynthesis.cancel()
    const profile = voiceProfileFor(name)
    const utterance = new SpeechSynthesisUtterance(clean)
    const voice = pickVoice(profile)
    if (voice) utterance.voice = voice
    utterance.lang = 'zh-CN'
    utterance.pitch = profile.pitch
    utterance.rate = profile.rate * (clean.length > 300 ? Math.min(1.28, 1 + (clean.length - 300) / 900) : 1)
    utterance.volume = profile.volume

    utterance.onstart = () => {
      state.speaking = true
      state.seat = seat
      state.name = name
      state.voiceName = voice?.name || '系统默认中文音色'
      state.error = ''
    }
    utterance.onend = () => finish()
    utterance.onerror = (event) => {
      const reason = event?.error || ''
      if (reason && !['canceled', 'interrupted'].includes(reason)) {
        state.error = `语音播放失败：${reason}`
      }
      finish()
    }

    current = utterance
    state.error = ''
    window.speechSynthesis.speak(utterance)
    return true
  }

  function stop() {
    if (!supported) return
    window.speechSynthesis.cancel()
    finish()
  }

  function toggle() {
    state.enabled = !state.enabled
    localStorage.setItem(ENABLED_KEY, state.enabled ? '1' : '0')
    if (!state.enabled) stop()
    return state.enabled
  }

  function test() {
    return speak({
      text: '我是沈砚。这轮先听我说完，别急着站边。',
      name: '沈砚',
      force: true,
    })
  }

  return { state, speak, stop, toggle, test }
}
