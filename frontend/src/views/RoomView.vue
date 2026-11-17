<template>
  <div class="room">
    <header class="room-head">
      <div class="room-head__left">
        <router-link to="/" class="room-head__logo" aria-label="返回首页">
          <AppLogo compact />
        </router-link>
        <span class="room-head__divider"></span>
        <div class="room-head__title">
          <strong class="serif">{{ room?.name || '牌局' }}</strong>
          <span v-if="room">房间 {{ room.code }} · {{ room.variant.name }}</span>
        </div>
      </div>

      <div class="room-head__status">
        <PhasePill v-if="game" :phase="game.phase" :day="game.day" />
        <span v-else-if="room" class="chip">{{ room.status === 'lobby' ? '候场中' : room.status }}</span>
        <span class="room-head__conn" :class="{ 'is-online': store.connected }">
          <i></i>{{ store.connected ? `${store.latency || 0}ms` : store.reconnecting ? '重连中' : '离线' }}
        </span>
      </div>

      <div class="room-head__actions">
        <VoiceOutputControl v-if="room?.status === 'playing' || room?.status === 'finished'" />
        <button class="room-head__code" type="button" title="复制房间号" @click="copyCode">
          {{ room?.code || code }}
          <span>复制</span>
        </button>
        <el-button
          v-if="store.isHost && room?.status === 'playing'"
          class="btn-ghost"
          size="small"
          @click="advancePhase"
        >
          推进阶段
        </el-button>
        <el-button v-if="room?.status === 'finished'" class="btn-gold" size="small" @click="store.requestReview()">
          查看复盘
        </el-button>
        <el-button class="btn-ghost room-head__leave" size="small" @click="leaveRoom">退出</el-button>
      </div>
    </header>

    <main v-if="loading" class="room__loading">
      <div class="room__loading-mark"></div>
      <p>正在连接牌桌…</p>
    </main>

    <main v-else-if="loadError" class="room__error panel">
      <span class="room__error-mark">◈</span>
      <h1 class="serif">找不到这张牌桌</h1>
      <p>{{ loadError }}</p>
      <el-button class="btn-gold" @click="router.push('/')">返回首页</el-button>
    </main>

    <main v-else-if="!store.you || !store.session" class="room__join">
      <section class="panel room__join-card">
        <div class="eyebrow">JOIN THE TABLE</div>
        <h1 class="serif">{{ room?.name }}</h1>
        <div class="room__join-meta">
          <span class="chip chip--gold">{{ room?.variant.name }}</span>
          <span class="chip">{{ room?.variant.subtitle }}</span>
          <span class="chip">{{ room?.mode === 'practice' ? '训练局 · AI 补位' : '标准局 · 至少 9 人' }}</span>
          <span class="chip">房间 {{ room?.code }}</span>
        </div>
        <p class="room__join-copy">
          {{ room?.status === 'lobby'
            ? (room?.mode === 'practice'
                ? '训练局：1 人也能开，未认领的 AI 会自动补位，完整跑完一局。'
                : '标准局：一人一个 AI，至少 9 名玩家才能开局；加入后认领一个 AI。')
            : room?.status === 'playing'
              ? '对局进行中。加入后以观战身份进入，可以看公开信息与 AI 发言。'
              : '这局已经结束。加入后可以查看牌桌与完整复盘。' }}
        </p>
        <div class="room__join-form">
          <el-input v-model="joinName" maxlength="16" placeholder="你的玩家代号" @keyup.enter="joinRoom" />
          <el-button class="btn-gold" :loading="joining" @click="joinRoom">进入牌桌</el-button>
        </div>
        <div class="room__join-roster" v-if="room?.teams?.length">
          <span v-for="team in room.teams" :key="team.seat" class="room__join-seat">
            <b>{{ team.seat }}</b>{{ team.ai.name }}
            <i v-if="team.advisorCount">{{ team.advisorCount }}/1</i>
          </span>
        </div>
      </section>
    </main>

    <main v-else-if="room?.status === 'lobby'" class="room__lobby">
      <LobbyBoard
        :room="room"
        :you="store.you"
        :starting="starting"
        :lobby-messages="store.lobbyChat"
        @assign="assignTeam"
        @start="startGame"
        @open-key="openKey"
        @lobby-chat="sendLobbyChat"
      />
    </main>

    <main v-else class="room__game">
      <IdentityCard
        v-if="store.team && store.privateInfo?.you"
        :team="store.team"
        :private-info="store.privateInfo"
        :game="game"
        :you="store.you"
      />
      <div class="room__timeline">
        <PhaseTimeline :phase="game?.phase || 'idle'" :day="game?.day || 0" :timings="room.timings" />
        <div class="room__timeline-side">
          <span class="muted">{{ store.you.isSpectator ? '观战中' : `辅佐 ${store.you.teamSeat} 号 ${myAi.name}` }}</span>
          <span v-if="store.you.isHost" class="chip chip--gold">房主</span>
        </div>
      </div>

      <div class="room__grid">
        <section class="room__left">
          <div class="panel room__stage">
            <div class="room__stage-head">
              <div class="room__stage-title">
                <span class="eyebrow">THE TABLE</span>
                <span class="muted">第 {{ game?.day || 0 }} 天 · {{ info.label }}</span>
              </div>
              <div class="room__stage-timer">
                <span v-if="remainingText">{{ remainingText }}</span>
                <span class="muted">{{ phaseHint }}</span>
              </div>
            </div>

            <GameTable
              :players="game?.players || []"
              :teams="room?.teams || []"
              :current-speaker="game?.currentSpeaker"
              :vote-counts="voteCounts"
              :my-team-seat="store.you.teamSeat"
              :reveal="room?.status === 'finished'"
              :wolf-mates="wolfMateSeats"
            >
              <template #center>
                <div class="table-center">
                  <CountdownRing
                    :ends-at="game?.phaseEndsAt || 0"
                    :total="phaseTotal"
                    :offset="store.serverOffset"
                    :size="126"
                    :tone="info.tone === 'red' ? 'red' : info.tone === 'violet' ? 'violet' : 'gold'"
                    :sub="info.hint"
                  >
                    <span class="table-center__label serif">{{ info.label }}</span>
                  </CountdownRing>
                  <div class="table-center__speaker" v-if="currentSpeaker">
                    <AvatarOrb :avatar="currentSpeaker.avatar" :color="currentSpeaker.color" :size="30" :speaking="true" />
                    <span>{{ currentSpeaker.name }} 发言中</span>
                  </div>
                  <div v-else class="table-center__day">DAY {{ String(game?.day || 0).padStart(2, '0') }}</div>
                </div>
              </template>
            </GameTable>

            <SpeechStage
              :game="game"
              :latest-speech="store.latestSpeech"
              :thinking="store.thinking"
              :last-words="store.lastWords"
              :team-seat="store.you.teamSeat"
              @replay="replayCurrentSpeech"
            />
          </div>

          <EventFeed :feed="store.feed" />
        </section>

        <CouncilPanel
          class="room__council"
          :room="room"
          :game="game"
          :team="store.team"
          :private-info="store.privateInfo"
          :you="store.you"
          :players="game?.players || []"
          @chat="sendChat"
          @submit="submitStrategy"
          @vote="submitVote"
          @night-order="submitNightOrder"
          @open-key="openKey(store.you.teamSeat)"
        />
      </div>
    </main>

    <KeyConfigDialog
      v-model="keyDialog"
      :room="room"
      :team-seat="keySeat"
      @saved="keyDialog = false"
    />

    <ReviewPanel
      :model-value="store.showReview"
      :review="store.review"
      @close="store.dismissReview()"
      @home="goHome"
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import AppLogo from '@/components/common/AppLogo.vue'
import AvatarOrb from '@/components/common/AvatarOrb.vue'
import CountdownRing from '@/components/common/CountdownRing.vue'
import PhasePill from '@/components/common/PhasePill.vue'
import LobbyBoard from '@/components/lobby/LobbyBoard.vue'
import KeyConfigDialog from '@/components/lobby/KeyConfigDialog.vue'
import GameTable from '@/components/game/GameTable.vue'
import SpeechStage from '@/components/game/SpeechStage.vue'
import PhaseTimeline from '@/components/game/PhaseTimeline.vue'
import EventFeed from '@/components/game/EventFeed.vue'
import IdentityCard from '@/components/game/IdentityCard.vue'
import CouncilPanel from '@/components/game/CouncilPanel.vue'
import ReviewPanel from '@/components/game/ReviewPanel.vue'
import VoiceOutputControl from '@/components/game/VoiceOutputControl.vue'
import { api } from '@/services/api'
import { useGameStore } from '@/stores/game'
import { useVoice } from '@/composables/useVoice'
import { useSpeech } from '@/composables/useSpeech'
import { phaseInfo } from '@/utils/game'
import { useCountdown } from '@/composables/useCountdown'

const route = useRoute()
const router = useRouter()
const store = useGameStore()
const voice = useVoice()
const speech = useSpeech()

const code = computed(() => String(route.params.code || '').toUpperCase())
const publicRoom = ref(null)
const loading = ref(true)
const loadError = ref('')
const joining = ref(false)
const starting = ref(false)
const keyDialog = ref(false)
const keySeat = ref(null)
const joinName = ref(localStorage.getItem('ai-werewolf-name') || '')

const room = computed(() => store.room || publicRoom.value)
const game = computed(() => store.game)
const info = computed(() => phaseInfo(game.value?.phase))

const myAi = computed(() => {
  const seat = store.you?.teamSeat
  return room.value?.teams?.find((t) => t.seat === seat)?.ai || { name: 'AI', avatar: '🐺' }
})

const phaseTotal = computed(() => {
  if (!room.value) return 0
  const map = {
    night_council: 'night_council',
    night: 'night',
    dawn: 'dawn',
    council: 'council',
    speech: 'speech',
    vote_advice: 'vote_advice',
    vote_reveal: 'vote_reveal',
    last_words: 'last_words',
    special: 'vote_reveal',
  }
  return room.value.timings?.[map[game.value?.phase]] || 0
})

const currentSpeaker = computed(() => {
  const seat = game.value?.currentSpeaker
  if (!seat) return null
  return game.value?.players?.find((p) => p.seat === seat) || null
})

const wolfMateSeats = computed(() => (store.privateInfo?.wolfMates || []).map((mate) => mate.seat))

const phaseHint = computed(() => {
  const map = {
    night_council: '夜间行动密谈',
    night: 'AI 正在行动',
    dawn: '公布死讯',
    council: '玩家密聊中',
    speech: 'AI 依次发言',
    vote_advice: '最后锁票',
    vote_reveal: '票型公开',
    last_words: '遗言',
    special: '技能结算',
    finished: '复盘',
  }
  return map[game.value?.phase] || '等待开始'
})

const remainingText = useCountdown(
  computed(() => game.value?.phaseEndsAt || 0),
  phaseTotal,
  computed(() => store.serverOffset),
).label

const voteCounts = computed(() => {
  if (store.voteResult?.counts) return store.voteResult.counts
  const votes = game.value?.board?.votes || []
  const last = votes[votes.length - 1]
  if (!last?.votes) return {}
  return last.votes.reduce((acc, v) => {
    if (v.to) acc[v.to] = (acc[v.to] || 0) + 1
    return acc
  }, {})
})

onMounted(async () => {
  await loadPublic()
  if (store.session?.code === code.value) {
    store.connect()
  } else if (store.session) {
    store.disconnect({ clear: true })
  }
})

onBeforeUnmount(() => {
  speech.stop()
  if (voice.state.joined) voice.leave()
  store.disconnect()
})

watch(code, async () => {
  if (voice.state.joined) voice.leave()
  speech.stop()
  await loadPublic()
  if (store.session?.code === code.value) store.connect()
})

watch(
  () => store.latestSpeech,
  (payload) => {
    if (payload?.text) speakPayload(payload)
  },
)

watch(
  () => store.lastWords,
  (payload) => {
    if (payload?.text) speakPayload(payload)
  },
)

watch(
  () => game.value?.phase,
  (phase) => {
    if (!['speech', 'last_words'].includes(phase)) speech.stop()
  },
)

async function loadPublic() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await api.getRoom(code.value)
    publicRoom.value = data.room
  } catch (err) {
    loadError.value = err.message || '房间不存在'
  } finally {
    loading.value = false
  }
}

async function joinRoom() {
  if (!joinName.value.trim()) {
    ElMessage.warning('先输入你的代号')
    return
  }
  joining.value = true
  try {
    localStorage.setItem('ai-werewolf-name', joinName.value.trim())
    await store.joinRoom(code.value, { name: joinName.value.trim(), spectator: false })
    await loadPublic()
    store.connect()
  } catch (err) {
    ElMessage.error(err.message || '加入失败')
  } finally {
    joining.value = false
  }
}

async function assignTeam(seat) {
  try {
    await api.assignTeam(code.value, store.session, seat)
  } catch (err) {
    ElMessage.error(err.message || '入座失败')
  }
}

async function startGame() {
  starting.value = true
  try {
    await api.startGame(code.value, store.session)
    await loadPublic()
  } catch (err) {
    ElMessage.error(err.message || '无法开始对局')
  } finally {
    starting.value = false
  }
}

async function advancePhase() {
  try {
    await api.advance(code.value, store.session)
  } catch (err) {
    ElMessage.error(err.message || '推进失败')
  }
}

function openKey(seat) {
  if (room.value?.status !== 'lobby') {
    ElMessage.info('API Key 只能在开局前配置，下一局再接入吧')
    return
  }
  if (!seat) {
    ElMessage.info('先选择一个智囊团')
    return
  }
  keySeat.value = seat
  keyDialog.value = true
}

function sendChat(text) {
  store.send('chat', { text })
}

function sendLobbyChat(text) {
  store.send('lobby_chat', { text })
}

function speakPayload(payload) {
  if (!payload?.text) return
  const player = game.value?.players?.find((p) => p.seat === payload.seat)
  speech.speak({
    text: payload.text,
    name: player?.name || payload.name || '',
    seat: payload.seat,
  })
}

function replayCurrentSpeech() {
  const last = (game.value?.speeches || []).slice(-1)[0]
  const payload =
    game.value?.phase === 'last_words' && store.lastWords
      ? store.lastWords
      : store.latestSpeech || last || store.lastWords
  if (!payload) return
  const player = game.value?.players?.find((p) => p.seat === payload.seat)
  speech.speak({
    text: payload.text,
    name: player?.name || payload.name || '',
    seat: payload.seat,
    force: true,
  })
}

function submitStrategy(pkg) {
  store.send('strategy', { package: pkg })
}

function submitVote(seat) {
  store.send('vote_advice', { seat })
}

function submitNightOrder(order) {
  store.send('night_order', { order })
}

async function copyCode() {
  try {
    await navigator.clipboard.writeText(room.value?.code || code.value)
    ElMessage.success('房间号已复制')
  } catch {
    ElMessage.info(room.value?.code || code.value)
  }
}

function leaveRoom() {
  if (voice.state.joined) voice.leave()
  store.disconnect({ clear: true })
  router.push('/')
}

function goHome() {
  if (voice.state.joined) voice.leave()
  store.disconnect({ clear: true })
  router.push('/')
}
</script>

<style scoped>
.room {
  min-height: 100vh;
  padding: 0 clamp(14px, 3vw, 34px) 30px;
  max-width: 1800px;
  margin: 0 auto;
}
.room-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  height: 68px;
  border-bottom: 1px solid var(--line);
}
.room-head__left {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}
.room-head__logo {
  display: inline-flex;
}
.room-head__divider {
  width: 1px;
  height: 24px;
  background: var(--line);
}
.room-head__title {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.room-head__title strong {
  font-size: 15px;
  font-weight: 500;
  letter-spacing: 0.04em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.room-head__title span {
  font-size: 8px;
  color: var(--muted);
  letter-spacing: 0.05em;
}
.room-head__status {
  display: flex;
  align-items: center;
  gap: 10px;
}
.room-head__conn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 8px;
  color: var(--muted);
}
.room-head__conn i {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--red);
}
.room-head__conn.is-online i {
  background: var(--green);
  box-shadow: 0 0 6px var(--green);
}
.room-head__actions {
  display: flex;
  align-items: center;
  gap: 7px;
}
.room-head__code {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 27px;
  padding: 0 9px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.02);
  color: var(--gold-soft);
  font-family: var(--serif);
  font-size: 11px;
  letter-spacing: 0.14em;
  cursor: pointer;
}
.room-head__code span {
  font-family: var(--sans);
  font-size: 7px;
  letter-spacing: 0;
  color: var(--muted);
}
.room__loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 20vh 0;
  color: var(--muted);
}
.room__loading-mark {
  width: 34px;
  height: 34px;
  border: 1px solid var(--line);
  border-top-color: var(--gold);
  border-radius: 50%;
  animation: spin-slow 1.2s linear infinite;
}
.room__loading p {
  font-size: 10px;
  letter-spacing: 0.14em;
}
.room__error {
  max-width: 440px;
  margin: 16vh auto 0;
  padding: 38px;
  text-align: center;
}
.room__error-mark {
  color: var(--gold);
  font-size: 28px;
}
.room__error h1 {
  margin: 12px 0 8px;
  font-weight: 500;
}
.room__error p {
  margin: 0 0 18px;
  font-size: 11px;
  color: var(--muted);
}
.room__join {
  display: grid;
  place-items: center;
  padding: 10vh 0;
}
.room__join-card {
  width: min(640px, 100%);
  padding: clamp(24px, 4vw, 42px);
}
.room__join-card h1 {
  margin: 12px 0 14px;
  font-size: clamp(32px, 5vw, 48px);
  font-weight: 500;
  line-height: 1.1;
}
.room__join-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.room__join-copy {
  margin: 16px 0 20px;
  font-size: 11px;
  line-height: 1.85;
  color: var(--muted);
}
.room__join-form {
  display: flex;
  gap: 8px;
}
.room__join-form .el-input {
  flex: 1;
}
.room__join-roster {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 22px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}
.room__join-seat {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 7px;
  border: 1px solid var(--line);
  border-radius: 5px;
  font-size: 9px;
  color: var(--muted);
}
.room__join-seat b {
  font-family: var(--serif);
  color: var(--gold);
  font-weight: 500;
}
.room__join-seat i {
  font-style: normal;
  color: rgba(79, 155, 130, 0.8);
}
.room__lobby {
  padding-top: 18px;
}
.room__game {
  padding-top: 12px;
}
.room__game > .identity-strip {
  margin-bottom: 8px;
}
.room__timeline {
  display: flex;
  align-items: center;
  gap: 10px;
}
.room__timeline > :first-child {
  flex: 1;
  min-width: 0;
}
.room__timeline-side {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 8px;
  white-space: nowrap;
}
.room__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 390px;
  gap: 12px;
  align-items: start;
  margin-top: 10px;
}
.room__left {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}
.room__stage {
  padding: 12px;
}
.room__stage-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 12px;
  padding: 2px 4px 10px;
}
.room__stage-title {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.room__stage-title .muted {
  font-size: 9px;
}
.room__stage-timer {
  display: flex;
  align-items: baseline;
  gap: 9px;
  font-family: var(--serif);
  font-size: 12px;
  color: var(--gold-soft);
}
.room__stage-timer .muted {
  font-family: var(--sans);
  font-size: 8px;
}
.room__council {
  position: sticky;
  top: 10px;
  height: calc(100vh - 90px);
  max-height: 860px;
  min-height: 560px;
}
.table-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 9px;
  text-align: center;
}
.table-center__label {
  font-size: 12px;
  letter-spacing: 0.1em;
  color: var(--gold-soft);
}
.table-center__speaker {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px 3px 4px;
  border-radius: 99px;
  border: 1px solid rgba(216, 178, 106, 0.22);
  background: rgba(9, 13, 16, 0.7);
  font-size: 8px;
  color: var(--text-soft);
  white-space: nowrap;
}
.table-center__day {
  font-family: var(--serif);
  font-size: 9px;
  letter-spacing: 0.28em;
  color: var(--muted);
}

@media (max-width: 1260px) {
  .room__grid {
    grid-template-columns: minmax(0, 1fr) 350px;
  }
}
@media (max-width: 1120px) {
  .room__grid {
    grid-template-columns: 1fr;
  }
  .room__council {
    position: static;
    height: auto;
    max-height: none;
    min-height: 0;
  }
}
@media (max-width: 860px) {
  .room-head {
    height: auto;
    padding: 10px 0;
    flex-wrap: wrap;
    gap: 8px;
  }
  .room-head__status {
    order: 3;
  }
  .room-head__actions {
    margin-left: auto;
  }
  .room-head__title span {
    display: none;
  }
  .room-head__leave {
    display: none;
  }
  .room__timeline {
    flex-direction: column;
    align-items: stretch;
  }
  .room__timeline-side {
    justify-content: flex-end;
  }
  .room__stage-head {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
}
@media (max-width: 560px) {
  .room {
    padding: 0 10px 20px;
  }
  .room__join-form {
    flex-direction: column;
  }
  .room__join-card {
    padding: 22px;
  }
}
</style>
