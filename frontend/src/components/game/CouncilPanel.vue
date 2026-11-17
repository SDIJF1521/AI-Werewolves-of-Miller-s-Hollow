<template>
  <aside class="council panel">
    <template v-if="!you.teamSeat">
      <div class="council__spectator">
        <span class="council__spectator-mark">◈</span>
        <div class="eyebrow">SPECTATOR</div>
        <h2 class="serif">你在观战</h2>
        <p>加入一个 AI 的智囊团，才能在 80 秒密聊里影响它。观战可以看公开板、AI 发言和投票。</p>
        <div class="council__spectator-actions">
          <span class="chip">{{ room.playerCount }} 个 AI</span>
          <span class="chip">{{ room.staffedTeams }} 个智囊团</span>
        </div>
      </div>
      <div class="council__section">
        <div class="council__section-head"><span>公开板</span></div>
        <BoardSummary :game="game" />
      </div>
    </template>

    <template v-else>
      <header class="council__ai">
        <div class="council__ai-top">
          <AvatarOrb :avatar="ai.avatar" :color="ai.color" :size="52" :speaking="game?.currentSpeaker === team.seat" />
          <div class="council__ai-meta">
            <div class="council__ai-name">
              <strong class="serif">{{ ai.name }}</strong>
              <span class="chip chip--gold">{{ privateInfo?.you?.roleName || '未知身份' }}</span>
            </div>
            <span class="council__ai-title">{{ ai.title }} · {{ aiStatusLabel }}</span>
          </div>
          <button class="council__key-btn" type="button" @click="$emit('open-key')">
            {{ team?.hasKey ? 'KEY' : '接入 AI' }}
          </button>
        </div>
        <div class="council__trust">
          <span>信任度</span>
          <div class="council__trust-bar"><i :style="{ width: `${Math.round((privateInfo?.you?.trust || 0.5) * 100)}%` }"></i></div>
          <strong>{{ Math.round((privateInfo?.you?.trust || 0.5) * 100) }}%</strong>
        </div>
        <div class="council__tags">
          <span v-if="privateInfo?.you?.camp === 'wolf'" class="chip chip--red">狼人阵营</span>
          <span v-else class="chip chip--green">好人阵营</span>
          <span class="chip">{{ team.members.length }}/3 玩家</span>
          <span v-if="team.key?.hasKey" class="chip chip--gold">{{ team.key.model }}</span>
          <span v-else class="chip">演示脑</span>
        </div>
        <div v-if="privateInfo?.wolfMates?.length" class="council__wolf-team">
          <span class="council__wolf-label">你的狼队友</span>
          <span
            v-for="mate in privateInfo.wolfMates"
            :key="mate.seat"
            class="council__wolf-mate"
            :class="{ 'is-dead': !mate.alive }"
          >
            {{ mate.seat }} 号 {{ mate.name }} · {{ mate.roleName }}
          </span>
        </div>
      </header>

      <div class="council__voice">
        <VoicePanel v-if="you.teamSeat" :allowed="voiceAllowed" mode="team" compact />
        <div v-else class="council__voice-note">
          加入一个 AI 的智囊团后，可随时和同一 AI 的 1–3 名军师连麦；其他 AI 听不到。
        </div>
      </div>

      <div class="council__tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="council__tab"
          :class="{ 'is-active': activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
          <i v-if="tab.key === 'chat' && chatAllowed" class="council__live-dot"></i>
        </button>
      </div>

      <div class="council__body">
        <template v-if="activeTab === 'chat'">
          <div class="council__phase-note" :class="{ 'is-open': chatAllowed }">
            <span class="council__phase-dot"></span>
            {{ phaseNote }}
          </div>

          <ChatStream
            :messages="team.chat || []"
            :allowed="chatAllowed"
            :you-id="you.id"
            @send="$emit('chat', $event)"
          />

          <div v-if="team.nightFeedback" class="council__feedback council__night-feedback">
            <div class="council__section-head"><span>昨夜行动反馈</span><span class="chip">{{ team.nightFeedback.label }}</span></div>
            <p>{{ team.nightFeedback.summary }}</p>
          </div>

          <div v-if="game?.phase === 'night_council'" class="council__strategy">
            <NightOrderForm
              :game="game"
              :team="team"
              :you="you"
              :private-info="privateInfo"
              :players="players"
              @submit="$emit('night-order', $event)"
            />
          </div>

          <div v-else-if="game?.phase === 'council'" class="council__strategy">
            <StrategyForm
              :game="game"
              :team="team"
              :players="players"
              :you="you"
              :disabled="false"
              @submit="$emit('submit', $event)"
            />
          </div>

          <VoteAdvicePanel
            v-else-if="game?.phase === 'vote_advice'"
            :players="players"
            :team="team"
            :you="you"
            @vote="$emit('vote', $event)"
          />

          <div v-else class="council__waiting">
            <span>{{ phaseInfo(game?.phase).label }}</span>
            <p>{{ phaseHint }}</p>
          </div>

          <div v-if="latestFeedback" class="council__feedback">
            <div class="council__section-head"><span>上一轮 AI 反馈</span></div>
            <FeedbackBadge :feedback="latestFeedback" />
            <p>{{ latestFeedback.summary }}</p>
            <small v-if="latestFeedback.detail">{{ latestFeedback.detail }}</small>
          </div>
        </template>

        <template v-else-if="activeTab === 'intel'">
          <BoardSummary :game="game" />
          <div class="council__section">
            <div class="council__section-head"><span>本队智囊团</span><small>1–3 名玩家 · Key 持有者权重 ×2</small></div>
            <div class="council__weights">
              <div v-for="member in team.members" :key="member.id" class="council__weight">
                <span>{{ member.name }}</span>
                <i v-if="member.hasKey" class="is-key">KEY</i>
                <i v-if="!member.connected" class="is-offline">离线</i>
                <strong>{{ member.weight?.toFixed(1) }}× · {{ member.hasKey ? 'LLM' : '玩家' }}</strong>
              </div>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="council__section">
            <div class="council__section-head"><span>身份与技能</span><span class="chip chip--gold">{{ privateInfo?.you?.roleName }}</span></div>
            <p class="council__role-summary">{{ privateInfo?.you?.summary }}</p>
            <p class="council__role-ability">{{ privateInfo?.you?.ability }}</p>
          </div>

          <div v-if="privateInfo?.wolfMates?.length" class="council__section">
            <div class="council__section-head"><span>狼队友</span></div>
            <div class="council__mates">
              <span v-for="mate in privateInfo.wolfMates" :key="mate.seat" :class="{ dead: !mate.alive }">
                {{ mate.seat }} 号 {{ mate.name }} · {{ mate.roleName }}
              </span>
            </div>
          </div>

          <div v-if="privateInfo?.you?.checks?.length" class="council__section">
            <div class="council__section-head"><span>预言家查验</span></div>
            <div class="council__checks">
              <span v-for="check in privateInfo.you.checks" :key="`${check.day}-${check.target}`" :class="check.result">
                D{{ check.day }} · {{ check.target }} 号 {{ check.result === 'wolf' ? '查杀' : '金水' }}
              </span>
            </div>
          </div>

          <div class="council__section">
            <div class="council__section-head"><span>AI 状态</span></div>
            <div class="council__status-grid">
              <div><span>模式</span><strong>{{ aiStatusLabel }}</strong></div>
              <div><span>模型</span><strong>{{ privateInfo?.aiStatus?.model || '本地演示脑' }}</strong></div>
              <div><span>密钥</span><strong>{{ team.key?.hasKey ? '已绑定' : '未绑定' }}</strong></div>
              <div><span>信任度</span><strong>{{ Math.round((privateInfo?.you?.trust || 0.5) * 100) }}%</strong></div>
            </div>
            <p v-if="privateInfo?.aiStatus?.lastError" class="council__error">
              上次模型调用失败：{{ privateInfo.aiStatus.lastError }}（已自动回退演示脑）
            </p>
          </div>

          <div v-if="feedbackHistory.length" class="council__section">
            <div class="council__section-head"><span>采纳记录</span></div>
            <div class="council__history">
              <div v-for="item in feedbackHistory" :key="item.at" class="council__history-item">
                <span>D{{ item.day }} · {{ item.seat }} 号</span>
                <FeedbackBadge :feedback="item.feedback" compact />
                <p>{{ item.feedback?.detail || item.feedback?.summary }}</p>
              </div>
            </div>
          </div>
        </template>
      </div>
    </template>
  </aside>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import AvatarOrb from '@/components/common/AvatarOrb.vue'
import BoardSummary from './BoardSummary.vue'
import ChatStream from './ChatStream.vue'
import FeedbackBadge from './FeedbackBadge.vue'
import NightOrderForm from './NightOrderForm.vue'
import StrategyForm from './StrategyForm.vue'
import VoteAdvicePanel from './VoteAdvicePanel.vue'
import VoicePanel from '@/components/lobby/VoicePanel.vue'
import { phaseInfo } from '@/utils/game'

const props = defineProps({
  room: { type: Object, required: true },
  game: { type: Object, default: null },
  team: { type: Object, default: null },
  privateInfo: { type: Object, default: null },
  you: { type: Object, required: true },
  players: { type: Array, default: () => [] },
})
defineEmits(['chat', 'submit', 'vote', 'open-key', 'night-order'])

const activeTab = ref('chat')
const tabs = [
  { key: 'chat', label: '密聊' },
  { key: 'intel', label: '情报' },
  { key: 'ai', label: '我的 AI' },
]

const ai = computed(() => props.room.teams.find((t) => t.seat === props.you.teamSeat)?.ai || { name: 'AI', avatar: '🐺', title: '', color: '#8a9b6e' })
const chatAllowed = computed(() => ['night_council', 'council', 'vote_advice'].includes(props.game?.phase))
const voiceAllowed = computed(() => Boolean(props.you.teamSeat && props.game))
const aiStatusLabel = computed(() => {
  const mode = props.privateInfo?.aiStatus?.mode
  if (mode === 'llm') return 'LLM 在线'
  if (mode === 'fallback') return '已回退演示脑'
  return '本地演示脑'
})
const phaseNote = computed(() => {
  if (props.game?.phase === 'night_council') return '夜间行动密谈开放 · 先定刀/验/救/守'
  if (props.game?.phase === 'council') return '80 秒密聊开放 · 语音/文字同步'
  if (props.game?.phase === 'vote_advice') return '锁票 30 秒 · 最后影响 AI 的机会'
  return '当前阶段密聊关闭'
})
const phaseHint = computed(() => {
  const map = {
    night_council: '先和 AI 对今夜行动。它会参考你的指令、其他 AI 的发言和此前票型。',
    night: 'AI 正在执行夜间行动，等待天亮。',
    dawn: '天亮了。先看死讯与公开板，准备下一轮密聊。',
    speech: 'AI 正在依次发言。听完再判断它有没有听懂你们。',
    special: '白天技能正在结算。',
    vote_reveal: '票型已公开。',
    last_words: '出局 AI 正在留遗言。',
    finished: '对局结束，打开复盘看 AI 的内心独白。',
  }
  return map[props.game?.phase] || '等待阶段推进。'
})
const latestFeedback = computed(() => {
  const list = props.game?.speeches || []
  for (let i = list.length - 1; i >= 0; i -= 1) {
    if (list[i].seat === props.you.teamSeat) return list[i].feedback
  }
  return null
})
const feedbackHistory = computed(() =>
  (props.game?.speeches || [])
    .filter((s) => s.seat === props.you.teamSeat && s.feedback)
    .slice(-4)
    .reverse(),
)

watch(
  () => props.game?.phase,
  (phase) => {
    if (phase === 'night_council' || phase === 'council' || phase === 'vote_advice') activeTab.value = 'chat'
  },
)
</script>

<style scoped>
.council {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
.council__spectator {
  padding: 30px 22px 20px;
  text-align: center;
  border-bottom: 1px solid var(--line);
}
.council__spectator-mark {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  margin: 0 auto 14px;
  border: 1px solid rgba(216, 178, 106, 0.3);
  border-radius: 50%;
  color: var(--gold);
  font-size: 18px;
}
.council__spectator h2 {
  margin: 8px 0;
  font-size: 26px;
  font-weight: 500;
}
.council__spectator p {
  margin: 0;
  font-size: 10px;
  line-height: 1.8;
  color: var(--muted);
}
.council__spectator-actions {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin-top: 16px;
}
.council__ai {
  padding: 16px 16px 12px;
  border-bottom: 1px solid var(--line);
}
.council__ai-top {
  display: flex;
  align-items: center;
  gap: 11px;
}
.council__ai-meta {
  flex: 1;
  min-width: 0;
}
.council__ai-name {
  display: flex;
  align-items: center;
  gap: 7px;
}
.council__ai-name strong {
  font-size: 20px;
  font-weight: 500;
  letter-spacing: 0.04em;
}
.council__ai-title {
  font-size: 8px;
  color: var(--muted);
}
.council__key-btn {
  flex: none;
  height: 23px;
  padding: 0 7px;
  border-radius: 6px;
  border: 1px solid rgba(216, 178, 106, 0.3);
  background: rgba(216, 178, 106, 0.08);
  color: var(--gold-soft);
  font-size: 8px;
  letter-spacing: 0.08em;
  cursor: pointer;
}
.council__trust {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 11px;
  font-size: 8px;
  color: var(--muted);
}
.council__trust-bar {
  flex: 1;
  height: 3px;
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.06);
  overflow: hidden;
}
.council__trust-bar i {
  display: block;
  height: 100%;
  border-radius: 99px;
  background: linear-gradient(90deg, var(--green), var(--gold));
}
.council__trust strong {
  font-family: var(--serif);
  color: var(--gold-soft);
  font-size: 10px;
  font-weight: 500;
}
.council__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 10px;
}
.council__wolf-team {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 5px;
  margin-top: 8px;
  padding: 7px 8px;
  border-radius: 8px;
  border: 1px solid rgba(198, 90, 79, 0.28);
  background: rgba(198, 90, 79, 0.07);
}
.council__wolf-label {
  font-size: 8px;
  letter-spacing: 0.08em;
  color: #e7a39b;
  white-space: nowrap;
}
.council__wolf-mate {
  font-size: 8px;
  color: #f0c4be;
  padding: 1px 5px;
  border-radius: 3px;
  background: rgba(198, 90, 79, 0.14);
  white-space: nowrap;
}
.council__wolf-mate.is-dead {
  opacity: 0.45;
  text-decoration: line-through;
}
.council__voice {
  padding: 10px 12px;
  border-bottom: 1px solid var(--line);
}
.council__voice-note {
  padding: 8px 9px;
  border: 1px dashed var(--line);
  border-radius: 8px;
  font-size: 8px;
  line-height: 1.6;
  color: var(--muted);
}
.council__tabs {
  display: flex;
  gap: 2px;
  padding: 6px 10px 0;
  border-bottom: 1px solid var(--line);
}
.council__tab {
  position: relative;
  padding: 7px 10px 9px;
  border: none;
  border-bottom: 1px solid transparent;
  background: transparent;
  color: var(--muted);
  font-size: 10px;
  cursor: pointer;
}
.council__tab.is-active {
  color: var(--gold-soft);
  border-bottom-color: var(--gold);
}
.council__live-dot {
  display: inline-block;
  width: 4px;
  height: 4px;
  margin-left: 4px;
  border-radius: 50%;
  background: var(--red);
  vertical-align: middle;
  animation: breathe 1.4s infinite;
}
.council__body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}
.council__phase-note {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--line);
  font-size: 8px;
  color: var(--muted);
}
.council__phase-note.is-open {
  border-color: rgba(216, 178, 106, 0.2);
  color: var(--gold-soft);
  background: rgba(216, 178, 106, 0.04);
}
.council__phase-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--muted);
}
.council__phase-note.is-open .council__phase-dot {
  background: var(--gold);
  box-shadow: 0 0 6px var(--gold);
}
.council__strategy {
  padding-top: 2px;
}
.council__waiting {
  padding: 18px 14px;
  border-radius: 10px;
  border: 1px dashed var(--line);
  text-align: center;
}
.council__waiting span {
  font-family: var(--serif);
  font-size: 15px;
  color: var(--gold-soft);
}
.council__waiting p {
  margin: 5px 0 0;
  font-size: 9px;
  line-height: 1.7;
  color: var(--muted);
}
.council__section {
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line);
}
.council__section:last-child {
  border-bottom: none;
}
.council__section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 9px;
}
.council__section-head > span:first-child {
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--text-soft);
}
.council__section-head small {
  font-size: 7px;
  color: var(--muted);
}
.council__weights {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.council__weight {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 7px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.025);
  font-size: 9px;
  color: var(--text-soft);
}
.council__weight i {
  font-style: normal;
  font-size: 7px;
  color: var(--gold);
}
.council__weight i.is-key {
  color: #9ed4c1;
}
.council__weight i.is-offline {
  color: #e1a49b;
}
.council__weight strong {
  margin-left: auto;
  font-family: var(--serif);
  color: var(--gold-soft);
  font-weight: 500;
}
.council__role-summary {
  margin: 0 0 6px;
  font-size: 11px;
  line-height: 1.7;
  color: var(--text);
}
.council__role-ability {
  margin: 0;
  font-size: 9px;
  line-height: 1.7;
  color: var(--muted);
}
.council__mates {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.council__mates span {
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(198, 90, 79, 0.1);
  border: 1px solid rgba(198, 90, 79, 0.25);
  color: #e7a39b;
}
.council__mates span.dead {
  opacity: 0.45;
  text-decoration: line-through;
}
.council__checks {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.council__checks span {
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--line);
}
.council__checks span.wolf {
  color: #e7a39b;
  border-color: rgba(198, 90, 79, 0.3);
  background: rgba(198, 90, 79, 0.08);
}
.council__checks span.good {
  color: #a8d6c4;
  border-color: rgba(79, 155, 130, 0.3);
  background: rgba(79, 155, 130, 0.08);
}
.council__status-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 5px;
}
.council__status-grid div {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 5px 7px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.025);
  font-size: 8px;
}
.council__status-grid span {
  color: var(--muted);
}
.council__status-grid strong {
  font-weight: 500;
  color: var(--text-soft);
  text-align: right;
}
.council__error {
  margin: 8px 0 0;
  font-size: 8px;
  line-height: 1.6;
  color: #e7a39b;
}
.council__feedback p {
  margin: 7px 0 0;
  font-size: 9px;
  line-height: 1.7;
  color: var(--muted);
}
.council__feedback small {
  display: block;
  margin-top: 4px;
  font-size: 9px;
  color: var(--text-soft);
  font-style: italic;
}
.council__history {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.council__history-item {
  padding: 7px;
  border-radius: 6px;
  border: 1px solid var(--line);
}
.council__history-item > span {
  font-size: 8px;
  color: var(--muted);
  margin-right: 5px;
}
.council__history-item p {
  margin: 5px 0 0;
  font-size: 8px;
  line-height: 1.6;
  color: var(--muted);
}
.council__night-feedback {
  padding: 9px;
  border: 1px solid rgba(111, 149, 187, 0.22);
  border-radius: 8px;
  background: rgba(111, 149, 187, 0.04);
}
</style>
