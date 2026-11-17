import { reactive } from 'vue'

import { api } from '@/services/api'
import { useGameStore } from '@/stores/game'

const state = reactive({
  joined: false,
  connecting: false,
  muted: false,
  error: '',
  localSpeaking: false,
  peers: {},
  secure: typeof window !== 'undefined' ? window.isSecureContext : true,
})

let localStream = null
let audioContext = null
let analyser = null
let analyserBuffer = null
let voiceTimer = null
let iceCache = null
let joining = false
const peerMap = new Map()
let unsubscribers = []

const FALLBACK_ICE = [
  { urls: 'stun:stun.l.google.com:19302' },
  { urls: 'stun:stun1.l.google.com:19302' },
]

async function getIceServers() {
  if (iceCache) return iceCache
  try {
    const data = await api.getIce()
    iceCache = data?.iceServers?.length ? data.iceServers : FALLBACK_ICE
  } catch {
    iceCache = FALLBACK_ICE
  }
  return iceCache
}

function setPeer(id, patch) {
  state.peers[id] = { ...(state.peers[id] || {}), ...patch }
}

function removePeer(id) {
  delete state.peers[id]
}

function sendSignal(target, signal) {
  const store = useGameStore()
  if (!store.connected) return
  store.send('voice_signal', { target, signal })
}

async function ensurePeer(memberId, name, initiator) {
  const existing = peerMap.get(memberId)
  if (existing) {
    if (name) setPeer(memberId, { name })
    return existing
  }

  const iceServers = await getIceServers()
  const pc = new RTCPeerConnection({ iceServers })
  const remoteAudio = document.createElement('audio')
  remoteAudio.autoplay = true
  remoteAudio.playsInline = true
  remoteAudio.style.display = 'none'
  document.body.appendChild(remoteAudio)

  const record = {
    pc,
    memberId,
    name: name || '',
    remoteAudio,
    pendingCandidates: [],
    makingOffer: false,
  }
  peerMap.set(memberId, record)
  setPeer(memberId, {
    name: name || '队友',
    connectionState: 'new',
    muted: false,
    speaking: false,
  })

  localStream?.getTracks().forEach((track) => pc.addTrack(track, localStream))

  pc.onicecandidate = (event) => {
    if (event.candidate) {
      sendSignal(memberId, { candidate: event.candidate.toJSON ? event.candidate.toJSON() : event.candidate })
    }
  }

  pc.ontrack = (event) => {
    const [stream] = event.streams
    if (stream) {
      remoteAudio.srcObject = stream
      remoteAudio.play().catch(() => {
        state.error = '浏览器阻止了自动播放，点击页面任意处恢复语音'
      })
    }
  }

  pc.onconnectionstatechange = () => {
    const connectionState = pc.connectionState
    setPeer(memberId, { connectionState })
    if (connectionState === 'failed') {
      try {
        pc.restartIce()
      } catch {
        /* ignore */
      }
    }
  }

  if (initiator) {
    await makeOffer(record)
  }
  return record
}

async function makeOffer(record) {
  try {
    record.makingOffer = true
    const offer = await record.pc.createOffer()
    await record.pc.setLocalDescription(offer)
    sendSignal(record.memberId, { description: record.pc.localDescription })
  } catch (err) {
    console.warn('offer failed', err)
  } finally {
    record.makingOffer = false
  }
}

async function handleSignal(from, fromName, signal) {
  if (!signal) return
  const record = await ensurePeer(from, fromName, false)
  const pc = record.pc

  try {
    if (signal.description) {
      const description = signal.description
      if (description.type === 'offer') {
        await pc.setRemoteDescription(description)
        for (const candidate of record.pendingCandidates.splice(0)) {
          await pc.addIceCandidate(candidate).catch(() => {})
        }
        const answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        sendSignal(from, { description: pc.localDescription })
      } else if (description.type === 'answer') {
        if (pc.signalingState !== 'stable') {
          await pc.setRemoteDescription(description)
          for (const candidate of record.pendingCandidates.splice(0)) {
            await pc.addIceCandidate(candidate).catch(() => {})
          }
        }
      }
    } else if (signal.candidate) {
      if (pc.remoteDescription?.type) {
        await pc.addIceCandidate(signal.candidate).catch(() => {})
      } else {
        record.pendingCandidates.push(signal.candidate)
      }
    }
  } catch (err) {
    console.warn('voice signal failed', err)
    state.error = '语音连接协商失败，请重新加入语音'
  }
}

function closePeer(memberId) {
  const record = peerMap.get(memberId)
  if (record) {
    try {
      record.pc.close()
    } catch {
      /* ignore */
    }
    record.remoteAudio.srcObject = null
    record.remoteAudio.remove()
    peerMap.delete(memberId)
  }
  removePeer(memberId)
}

function closeAllPeers() {
  for (const memberId of [...peerMap.keys()]) closePeer(memberId)
}

function bindEvents() {
  const store = useGameStore()
  unsubscribers.push(
    store.onEvent('voice_peers', async (payload) => {
      const peers = payload?.data?.peers || []
      for (const peer of peers) {
        await ensurePeer(peer.memberId, peer.name, true)
        setPeer(peer.memberId, { muted: Boolean(peer.muted) })
      }
    }),
    store.onEvent('voice_peer_joined', (payload) => {
      const data = payload?.data
      if (data?.memberId && data.memberId !== store.you?.id) {
        setPeer(data.memberId, { name: data.name, connectionState: 'connecting' })
      }
    }),
    store.onEvent('voice_peer_left', (payload) => {
      const data = payload?.data
      if (data?.memberId && data.memberId !== store.you?.id) closePeer(data.memberId)
    }),
    store.onEvent('voice_signal', (payload) => {
      if (payload?.from) handleSignal(payload.from, payload.fromName, payload.signal)
    }),
    store.onEvent('voice_state', (payload) => {
      const data = payload?.data
      if (!data?.memberId || data.memberId === store.you?.id) return
      setPeer(data.memberId, { muted: Boolean(data.muted), speaking: Boolean(data.speaking) })
    }),
    store.onEvent('voice_closed', () => {
      leave(false)
    }),
  )
}

function setupAnalyser() {
  const AudioCtx = window.AudioContext || window.webkitAudioContext
  if (!AudioCtx) return
  audioContext = new AudioCtx()
  const source = audioContext.createMediaStreamSource(localStream)
  analyser = audioContext.createAnalyser()
  analyser.fftSize = 512
  source.connect(analyser)
  analyserBuffer = new Uint8Array(analyser.fftSize)
  let lastSent = 0
  let lastSpeaking = false

  voiceTimer = window.setInterval(() => {
    if (!analyser || state.muted) {
      if (state.localSpeaking) {
        state.localSpeaking = false
        useGameStore().send('voice_state', { muted: state.muted, speaking: false })
      }
      return
    }
    analyser.getByteTimeDomainData(analyserBuffer)
    let sum = 0
    for (let i = 0; i < analyserBuffer.length; i += 1) {
      const v = (analyserBuffer[i] - 128) / 128
      sum += v * v
    }
    const rms = Math.sqrt(sum / analyserBuffer.length)
    const speaking = rms > 0.035
    state.localSpeaking = speaking
    const now = Date.now()
    if ((speaking !== lastSpeaking || now - lastSent > 1200) && now - lastSent > 250) {
      lastSpeaking = speaking
      lastSent = now
      useGameStore().send('voice_state', { muted: state.muted, speaking })
    }
  }, 140)
}

function teardown() {
  if (voiceTimer) window.clearInterval(voiceTimer)
  voiceTimer = null
  closeAllPeers()
  unsubscribers.forEach((off) => off())
  unsubscribers = []
  if (localStream) {
    localStream.getTracks().forEach((track) => track.stop())
    localStream = null
  }
  if (audioContext) {
    audioContext.close().catch(() => {})
    audioContext = null
  }
  analyser = null
  analyserBuffer = null
  state.joined = false
  state.connecting = false
  state.localSpeaking = false
  state.muted = false
}

async function join() {
  if (state.joined || joining) return
  const store = useGameStore()
  const inLobby = store.room?.status === 'lobby'
  if (!inLobby && !store.you?.teamSeat) {
    state.error = '先加入一个 AI 智囊团，才能使用队内语音'
    return
  }
  if (!state.secure) {
    state.error = '浏览器只允许 HTTPS 或 localhost 使用麦克风'
    return
  }
  joining = true
  state.connecting = true
  state.error = ''
  closeAllPeers()
  try {
    localStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
      video: false,
    })
    state.muted = false
    localStream.getAudioTracks().forEach((track) => {
      track.enabled = true
    })
    setupAnalyser()
    bindEvents()
    const sent = store.send('voice_join')
    if (!sent) throw new Error('实时连接尚未就绪')
    state.joined = true
  } catch (err) {
    teardown()
    state.error =
      err?.name === 'NotAllowedError'
        ? '麦克风权限被拒绝，请在浏览器地址栏允许麦克风'
        : err?.message || '无法加入语音'
  } finally {
    joining = false
    state.connecting = false
  }
}

function leave(notify = true) {
  if (state.joined && notify) {
    useGameStore().send('voice_leave')
  }
  teardown()
}

function toggleMute() {
  if (!localStream) return
  state.muted = !state.muted
  localStream.getAudioTracks().forEach((track) => {
    track.enabled = !state.muted
  })
  if (state.muted) state.localSpeaking = false
  useGameStore().send('voice_state', { muted: state.muted, speaking: state.localSpeaking })
}

export function useVoice() {
  return { state, join, leave, toggleMute }
}
