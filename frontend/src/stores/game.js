import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { api, websocketUrl } from '@/services/api'

const STORAGE_KEY = 'ai-werewolf-session-v1'

function loadSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw)
    if (!data?.code || !data?.playerId || !data?.token) return null
    return data
  } catch {
    return null
  }
}

function saveSession(session) {
  if (!session) {
    localStorage.removeItem(STORAGE_KEY)
    return
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
}

export const useGameStore = defineStore('game', () => {
  const session = ref(loadSession())
  const room = ref(null)
  const you = ref(null)
  const team = ref(null)
  const privateInfo = ref(null)
  const game = ref(null)
  const review = ref(null)
  const aiStatus = ref([])
  const connected = ref(false)
  const connecting = ref(false)
  const reconnecting = ref(false)
  const serverOffset = ref(0)
  const latency = ref(0)
  const lastError = ref('')
  const feed = ref([])
  const lobbyChat = ref([])
  const latestSpeech = ref(null)
  const thinking = ref(null)
  const lastWords = ref(null)
  const voteResult = ref(null)
  const showReview = ref(false)

  const handlers = new Map()
  let socket = null
  let reconnectTimer = null
  let pingTimer = null
  let lastPingAt = 0
  let attempts = 0
  let manualClose = false

  const phase = computed(() => game.value?.phase || (room.value?.status === 'lobby' ? 'lobby' : 'idle'))
  const isHost = computed(() => Boolean(you.value?.isHost))
  const inTeam = computed(() => Boolean(you.value?.teamSeat))
  const alivePlayers = computed(() => (game.value?.players || []).filter((p) => p.alive))
  const currentPlayer = computed(() => {
    const seat = game.value?.currentSpeaker
    return seat ? game.value?.players?.find((p) => p.seat === seat) || null : null
  })

  function onEvent(type, handler) {
    if (!handlers.has(type)) handlers.set(type, new Set())
    handlers.get(type).add(handler)
    return () => handlers.get(type)?.delete(handler)
  }

  function emit(type, data) {
    handlers.get(type)?.forEach((fn) => {
      try {
        fn(data)
      } catch (err) {
        console.error('[event]', type, err)
      }
    })
  }

  function pushFeed(item) {
    feed.value.unshift({
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      at: Date.now(),
      ...item,
    })
    if (feed.value.length > 40) feed.value.length = 40
  }

  function setSession(code, payload) {
    session.value = {
      code: code.toUpperCase(),
      playerId: payload.playerId,
      token: payload.token,
      name: payload.member?.name || '',
    }
    saveSession(session.value)
  }

  function clearSession() {
    session.value = null
    saveSession(null)
    room.value = null
    you.value = null
    team.value = null
    privateInfo.value = null
    game.value = null
    review.value = null
    feed.value = []
    showReview.value = false
    lobbyChat.value = []
  }

  function applySnapshot(data) {
    if (!data) return
    if (data.room) {
      room.value = data.room
      lobbyChat.value = data.room.lobbyChat || []
    }
    if (data.you) you.value = data.you
    if (data.team !== undefined) team.value = data.team
    if (data.private !== undefined) privateInfo.value = data.private
    if (data.game !== undefined) game.value = data.game
    if (data.review !== undefined) {
      const firstReview = !review.value
      review.value = data.review
      if (data.review && firstReview) showReview.value = true
    }
    if (data.aiStatus) aiStatus.value = data.aiStatus
    if (data.serverTime) {
      serverOffset.value = data.serverTime - Date.now()
    }
    if (data.game?.logs?.length && feed.value.length === 0) {
      feed.value = data.game.logs
        .slice(-20)
        .reverse()
        .map((log) => ({
          id: log.id || `${log.at}-${Math.random()}`,
          kind: log.kind,
          text: log.text,
          at: log.at,
        }))
    }
  }

  function handlePhase(data) {
    if (!game.value) return
    game.value = {
      ...game.value,
      phase: data.phase,
      day: data.day ?? game.value.day,
      phaseEndsAt: data.endsAt,
      currentSpeaker: data.currentSpeaker ?? null,
      timings: data.timings || game.value.timings,
    }
    thinking.value = null
    lastWords.value = null
    if (data.phase !== 'vote_reveal') voteResult.value = null
  }

  function handleMessage(payload) {
    switch (payload.type) {
      case 'snapshot':
        applySnapshot(payload.data)
        break
      case 'phase':
        handlePhase(payload.data)
        break
      case 'ai_thinking':
        thinking.value = payload.data
        break
      case 'speech':
        latestSpeech.value = payload.data
        thinking.value = null
        if (game.value) {
          game.value = {
            ...game.value,
            phaseEndsAt: payload.data.endsAt || game.value.phaseEndsAt,
            currentSpeaker: payload.data.seat,
          }
        }
        break
      case 'last_words':
        lastWords.value = payload.data
        if (game.value) {
          game.value = {
            ...game.value,
            phaseEndsAt: payload.data.endsAt || game.value.phaseEndsAt,
            currentSpeaker: payload.data.seat,
          }
        }
        break
      case 'vote_result':
        voteResult.value = payload.data
        pushFeed({ kind: 'vote', text: voteSummary(payload.data) })
        break
      case 'skill':
        pushFeed({ kind: 'skill', text: skillSummary(payload.data) })
        break
      case 'chat':
        if (team.value) {
          const list = [...(team.value.chat || []), payload.data]
          team.value = { ...team.value, chat: list.slice(-80) }
        }
        break
      case 'lobby_chat':
        if (!lobbyChat.value.some((m) => m.id === payload.data?.id)) {
          lobbyChat.value = [...lobbyChat.value, payload.data].slice(-80)
        }
        break
      case 'team_update':
        team.value = payload.data
        break
      case 'council_end':
        if (game.value) {
          game.value = { ...game.value, councilRounds: [...(game.value.councilRounds || []), payload.data] }
        }
        pushFeed({ kind: 'system', text: '策略包已锁定，AI 开始依次发言。' })
        break
      case 'night_orders_locked':
        pushFeed({ kind: 'system', text: '夜间指令已锁定，AI 开始行动。' })
        break
      case 'game_over':
        pushFeed({ kind: 'system', text: payload.data?.winReason || '对局结束。' })
        showReview.value = true
        ElMessage.success('对局结束，复盘已生成')
        emit('game_over', payload.data)
        break
      case 'error':
        lastError.value = payload.message
        ElMessage.error(payload.message)
        emit('error', payload.message)
        break
      case 'presence': {
        const data = payload.data
        if (!data || !room.value) break
        room.value.teams = room.value.teams.map((t) => ({
          ...t,
          members: t.members.map((m) =>
            m.id === data.memberId
              ? { ...m, connected: data.connected, reconnectDeadline: data.reconnectDeadline }
              : m,
          ),
        }))
        break
      }
      case 'member_removed': {
        const data = payload.data || {}
        pushFeed({ kind: 'system', text: `${data.name || '玩家'} 超过 60 秒未重连，已移出房间。` })
        break
      }
      case 'ai_offline': {
        const data = payload.data || {}
        if (room.value) {
          room.value.teams = room.value.teams.map((t) =>
            t.seat === data.seat ? { ...t, offline: true } : t,
          )
        }
        pushFeed({ kind: 'system', text: `${data.seat} 号 AI 已离线：不再调用 API，跳过发言、投票和夜间行动。` })
        break
      }
      case 'speech_skipped': {
        const data = payload.data || {}
        pushFeed({ kind: 'system', text: `${data.seat} 号 AI 已离线，跳过发言。` })
        break
      }
      case 'pong':
        latency.value = lastPingAt ? Math.max(0, Date.now() - lastPingAt) : 0
        break
      case 'voice_closed':
        pushFeed({ kind: 'system', text: payload.reason || '语音已关闭。' })
        emit('voice_closed', payload)
        break
      default:
        emit(payload.type, payload)
    }
  }

  function schedulePing() {
    clearInterval(pingTimer)
    pingTimer = setInterval(() => {
      if (socket?.readyState === WebSocket.OPEN) {
        lastPingAt = Date.now()
        socket.send(JSON.stringify({ type: 'ping' }))
      }
    }, 15000)
  }

  function scheduleReconnect() {
    if (manualClose || !session.value || reconnectTimer) return
    reconnecting.value = true
    const delay = Math.min(6000, 900 * 2 ** attempts)
    attempts += 1
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      connect()
    }, delay)
  }

  function connect() {
    if (!session.value) return
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return
    manualClose = false
    connecting.value = true
    const url = websocketUrl(session.value.code, session.value)
    const ws = new WebSocket(url)
    socket = ws

    ws.onopen = () => {
      connected.value = true
      connecting.value = false
      reconnecting.value = false
      attempts = 0
      schedulePing()
      emit('open')
    }

    ws.onmessage = (event) => {
      try {
        handleMessage(JSON.parse(event.data))
      } catch (err) {
        console.warn('invalid ws message', err)
      }
    }

    ws.onerror = () => {
      connected.value = false
    }

    ws.onclose = (event) => {
      connected.value = false
      connecting.value = false
      clearInterval(pingTimer)
      socket = null
      if (event.code === 4401) {
        ElMessage.error('身份已失效，请重新加入房间')
        clearSession()
        manualClose = true
        return
      }
      if (!manualClose) scheduleReconnect()
    }
  }

  function disconnect({ clear = false } = {}) {
    manualClose = true
    clearTimeout(reconnectTimer)
    reconnectTimer = null
    clearInterval(pingTimer)
    reconnecting.value = false
    if (socket) {
      socket.close(1000, 'leave')
      socket = null
    }
    connected.value = false
    if (clear) {
      clearSession()
      room.value = null
      you.value = null
      team.value = null
      privateInfo.value = null
      game.value = null
      review.value = null
      feed.value = []
    }
  }

  function send(type, payload = {}) {
    if (socket?.readyState !== WebSocket.OPEN) {
      ElMessage.warning('实时连接尚未就绪，请稍候')
      return false
    }
    socket.send(JSON.stringify({ type, ...payload }))
    return true
  }

  async function createRoom(payload) {
    const res = await api.createRoom(payload)
    setSession(res.code, res)
    return res
  }

  async function joinRoom(code, payload) {
    const res = await api.joinRoom(code, payload)
    setSession(code, res)
    return res
  }

  function requestReview() {
    showReview.value = true
  }

  function dismissReview() {
    showReview.value = false
  }

  return {
    session,
    room,
    you,
    team,
    privateInfo,
    game,
    review,
    aiStatus,
    connected,
    connecting,
    reconnecting,
    serverOffset,
    latency,
    lastError,
    feed,
    latestSpeech,
    thinking,
    lastWords,
    voteResult,
    showReview,
    lobbyChat,
    phase,
    isHost,
    inTeam,
    alivePlayers,
    currentPlayer,
    onEvent,
    connect,
    disconnect,
    send,
    createRoom,
    joinRoom,
    setSession,
    clearSession,
    requestReview,
    dismissReview,
  }
})

function voteSummary(data) {
  if (!data) return '投票结束。'
  if (data.tie) return '投票平票，本轮无人出局。'
  if (data.exile) return `${data.exile} 号被放逐。`
  return '本轮无人被放逐。'
}

const SKILL_LABELS = {
  knight_duel: '骑士决斗',
  white_wolf_explode: '白狼王自爆',
  idiot_reveal: '白痴翻牌',
  hunter_shot: '猎人开枪',
  wolf_king_shot: '狼王开枪',
}

function skillSummary(data) {
  if (!data) return '技能发动。'
  if (data.skill === 'idiot_reveal') return `${data.seat} 号翻开白痴牌，免于放逐。`
  if (data.skill === 'white_wolf_explode') return `${data.seat} 号白狼王自爆，带走了 ${data.target} 号。`
  if (data.skill === 'knight_duel') {
    return data.hit ? `骑士决斗命中 ${data.target} 号狼人！` : `骑士决斗 ${data.target} 号失败，骑士出局。`
  }
  return `${SKILL_LABELS[data.skill] || '技能'}：${data.seat || ''} → ${data.target || ''}`
}
