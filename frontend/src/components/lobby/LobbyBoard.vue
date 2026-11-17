<template>
  <div class="lobby">
    <section class="panel lobby__main">
      <header class="lobby__header">
        <div>
          <div class="eyebrow">WAITING ROOM</div>
          <h1 class="serif">{{ room.name }}</h1>
          <div class="lobby__meta">
            <span class="chip chip--gold">{{ room.variant.name }}</span>
            <span class="chip">{{ room.variant.subtitle }}</span>
            <span class="chip" :class="isPractice ? 'chip--green' : ''">{{ isPractice ? '训练局 · AI 补位' : '标准局 · 至少 9 人' }}</span>
            <span class="chip">{{ room.timing === 'fast' ? '快速局' : '标准局' }}</span>
            <span class="chip">房间 <b class="lobby__code">{{ room.code }}</b></span>
          </div>
        </div>
        <div class="lobby__header-actions">
          <el-button class="btn-ghost" size="small" @click="copyInvite">复制邀请</el-button>
          <el-button v-if="you.isHost" class="btn-gold" size="small" :loading="starting" :disabled="!canStart" @click="$emit('start')">
            {{ canStart ? '开始对局' : `还需 ${missingPlayers} 名玩家` }}
          </el-button>
        </div>
      </header>

      <div class="lobby__hint">
        <span class="lobby__hint-dot"></span>
        {{ isPractice
          ? '训练局：未认领的 AI 会自动补位，1 名玩家即可开完整对局。'
          : '标准局：一名玩家只能控制 1 个 AI，至少 9 名玩家才能开局。' }}
      </div>

      <div class="lobby__grid">
        <TeamCard
          v-for="team in room.teams"
          :key="team.seat"
          :team="team"
          :selected="selectedSeat === team.seat"
          :mine="you.teamSeat === team.seat"
          @select="selectTeam"
        />
      </div>
    </section>

    <aside class="lobby__side">
      <section class="panel lobby__side-card">
        <div class="lobby__side-head">
          <div>
            <div class="eyebrow">YOUR AI</div>
            <h2 class="serif">{{ selectedTeam ? selectedTeam.ai.name : '选择一个 AI' }}</h2>
          </div>
          <span v-if="selectedTeam" class="lobby__seat-no">{{ String(selectedTeam.seat).padStart(2, '0') }}</span>
        </div>

        <template v-if="selectedTeam">
          <div class="lobby__ai-line">
            <AvatarOrb :avatar="selectedTeam.ai.avatar" :color="selectedTeam.ai.color" :size="54" />
            <div>
              <strong>{{ selectedTeam.ai.title }}</strong>
              <span>{{ selectedTeam.advisorCount }} / 1 名玩家 · {{ selectedTeam.hasKey ? '已接入 LLM' : '本地演示脑' }}</span>
            </div>
          </div>

          <div class="lobby__members">
            <div v-for="member in selectedTeam.members" :key="member.id" class="lobby__member">
              <div class="lobby__member-name">
                <span class="lobby__member-dot" :class="{ 'is-you': member.id === you.id }"></span>
                <span>{{ member.name }}</span>
                <i v-if="member.hasKey">KEY</i>
              </div>
              <span class="lobby__weight">{{ member.hasKey ? 'LLM' : '玩家' }}</span>
            </div>
            <div v-if="!selectedTeam.members.length" class="lobby__empty">还没有玩家，AI 会自主行动。</div>
          </div>

          <div class="lobby__key-line" v-if="selectedTeam.hasKey">
            <span class="chip chip--green">Key 已绑定</span>
            <span class="muted">{{ selectedTeam.key.model }}</span>
            <span class="muted">{{ selectedTeam.key.maskedKey }}</span>
          </div>

          <div class="lobby__actions">
            <el-button
              v-if="you.teamSeat !== selectedTeam.seat"
              class="btn-gold"
              :disabled="selectedTeam.advisorCount >= 1"
              @click="$emit('assign', selectedTeam.seat)"
            >
              {{ selectedTeam.advisorCount >= 1 ? '该 AI 已有玩家' : '控制这个 AI' }}
            </el-button>
            <template v-else>
              <el-button class="btn-ghost" @click="$emit('open-key', selectedTeam.seat)">配置 API Key</el-button>
              <el-button class="btn-danger-ghost" @click="$emit('assign', null)">离开</el-button>
            </template>
          </div>

          <VoicePanel :allowed="true" mode="lobby" />
        </template>

        <div v-else class="lobby__empty-state">
          <span>🎭</span>
          <p>点击左侧任意 AI，查看它的性格与当前玩家；每个 AI 只能由 1 名玩家控制。</p>
        </div>
      </section>

      <section class="panel lobby__side-card lobby__players">
        <div class="lobby__side-head">
          <div>
            <div class="eyebrow">TABLE</div>
            <h2 class="serif">本局配置</h2>
          </div>
        </div>
        <ul class="lobby__facts">
          <li><span>玩家配置</span><strong>1 人控制 1 个 AI</strong></li>
          <li><span>模式</span><strong>{{ isPractice ? '训练局（AI 补位）' : '标准局' }}</strong></li>
          <li><span>开局门槛</span><strong>{{ isPractice ? '至少 1 人' : `至少 ${minPlayers} 人` }}</strong></li>
          <li><span>已就位</span><strong>{{ room.staffedTeams }} / {{ room.playerCount }} 名玩家</strong></li>
          <li><span>在线成员</span><strong>{{ room.memberCount }} 人</strong></li>
          <li><span>观战</span><strong>{{ room.spectatorCount }} 人</strong></li>
          <li><span>语音</span><strong>候场大厅 / 开局队内</strong></li>
          <li><span>计时</span><strong>{{ room.timings.council }}s 密聊 / {{ room.timings.speech }}s 发言</strong></li>
        </ul>
        <div class="lobby__start-note">
          <span v-if="you.isHost">
            {{ canStart
              ? (isPractice
                  ? `可以开局。${room.playerCount - room.staffedTeams} 个 AI 将由系统补位。`
                  : `已满足 ${minPlayers} 人开局条件。${room.staffedTeams < room.playerCount ? `剩余 ${room.playerCount - room.staffedTeams} 个 AI 将自主行动。` : '所有 AI 都有玩家。'}`)
              : `还需 ${missingPlayers} 名玩家才能开始。` }}
          </span>
          <span v-else>等待房主开始。{{ isPractice ? '训练局 AI 会自动补位。' : '每名玩家只能控制一个 AI。' }}</span>
        </div>
        <el-button v-if="you.isHost" class="btn-gold lobby__start" :loading="starting" :disabled="!canStart" @click="$emit('start')">
          {{ canStart ? '开始对局' : `还需 ${missingPlayers} 名玩家` }}
        </el-button>
        <div class="lobby__invite" @click="copyInvite">
          <span>邀请链接</span>
          <code>{{ inviteLink }}</code>
        </div>
      </section>

      <section class="panel lobby__side-card lobby__chat-card">
        <div class="lobby__side-head">
          <div>
            <div class="eyebrow">LOBBY TALK</div>
            <h2 class="serif">大厅交流</h2>
          </div>
          <span class="chip">{{ room.memberCount }} 人在场</span>
        </div>
        <ChatStream
          :messages="lobbyMessages"
          :allowed="room.status === 'lobby'"
          :you-id="you.id"
          compact
          title="候场大厅"
          empty-hint="开局前所有人都能在这里交流。选好 AI 后，还可以进小队语音。"
          placeholder="和候场的人聊聊…"
          disabled-hint="对局已开始，大厅频道已关闭"
          @send="$emit('lobby-chat', $event)"
        />
        <p class="lobby__chat-note">
          大厅语音最多 {{ room.maxLobbyVoice || 8 }} 人；开局后会切换为各 AI 的队内语音。
        </p>
      </section>
    </aside>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import AvatarOrb from '@/components/common/AvatarOrb.vue'
import TeamCard from './TeamCard.vue'
import VoicePanel from './VoicePanel.vue'
import ChatStream from '@/components/game/ChatStream.vue'

const props = defineProps({
  room: { type: Object, required: true },
  you: { type: Object, required: true },
  starting: { type: Boolean, default: false },
  lobbyMessages: { type: Array, default: () => [] },
})
const emit = defineEmits(['assign', 'start', 'open-key', 'lobby-chat'])

const selectedSeat = ref(props.you.teamSeat || props.room.teams?.[0]?.seat || 1)
const selectedTeam = computed(() => props.room.teams?.find((t) => t.seat === selectedSeat.value) || null)
const inviteLink = computed(() => `${window.location.origin}${window.location.pathname}#/room/${props.room.code}`)
const minPlayers = computed(() => (props.room.mode === 'practice' ? 1 : props.room.minPlayers || 9))
const isPractice = computed(() => props.room.mode === 'practice')
const canStart = computed(() => (props.room.staffedTeams || 0) >= minPlayers.value)
const missingPlayers = computed(() => Math.max(0, minPlayers.value - (props.room.staffedTeams || 0)))

watch(
  () => props.you.teamSeat,
  (seat) => {
    if (seat) selectedSeat.value = seat
  },
)

function selectTeam(seat) {
  selectedSeat.value = seat
}

async function copyInvite() {
  try {
    await navigator.clipboard.writeText(inviteLink.value)
    ElMessage.success('邀请链接已复制')
  } catch {
    ElMessage.info(inviteLink.value)
  }
}
</script>

<style scoped>
.lobby {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 14px;
  align-items: start;
}
.lobby__main {
  padding: clamp(18px, 2.5vw, 30px);
}
.lobby__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
}
.lobby__header h1 {
  margin: 10px 0 12px;
  font-size: clamp(28px, 3vw, 40px);
  font-weight: 500;
  line-height: 1.1;
}
.lobby__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.lobby__code {
  color: var(--gold-soft);
  letter-spacing: 0.14em;
  font-weight: 500;
}
.lobby__header-actions {
  display: flex;
  gap: 8px;
  flex: none;
}
.lobby__hint {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 22px 0 16px;
  padding: 9px 11px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.02);
  font-size: 10px;
  line-height: 1.6;
  color: var(--muted);
}
.lobby__hint-dot {
  width: 5px;
  height: 5px;
  margin-top: 5px;
  border-radius: 50%;
  background: var(--gold);
  flex: none;
}
.lobby__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 9px;
}
.lobby__side {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.lobby__side-card {
  padding: 20px;
}
.lobby__side-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
}
.lobby__side-head h2 {
  margin: 7px 0 0;
  font-size: 24px;
  font-weight: 500;
}
.lobby__seat-no {
  font-family: var(--serif);
  font-size: 26px;
  color: rgba(216, 178, 106, 0.35);
  line-height: 1;
}
.lobby__ai-line {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--line);
}
.lobby__ai-line div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.lobby__ai-line strong {
  font-size: 13px;
  font-weight: 500;
}
.lobby__ai-line span {
  font-size: 9px;
  color: var(--muted);
}
.lobby__members {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 12px 0;
}
.lobby__member {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.025);
  font-size: 11px;
}
.lobby__member-name {
  display: flex;
  align-items: center;
  gap: 6px;
}
.lobby__member-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--muted);
}
.lobby__member-dot.is-you {
  background: var(--green);
  box-shadow: 0 0 6px var(--green);
}
.lobby__member-name i {
  font-style: normal;
  font-size: 8px;
  color: var(--gold);
  padding: 0 4px;
  border: 1px solid rgba(216, 178, 106, 0.3);
  border-radius: 3px;
  line-height: 14px;
}
.lobby__member-name i.is-key {
  color: #a8d6c4;
  border-color: rgba(79, 155, 130, 0.3);
}
.lobby__weight {
  font-family: var(--serif);
  font-size: 12px;
  color: var(--gold-soft);
}
.lobby__empty {
  font-size: 10px;
  color: var(--muted);
  padding: 8px 0;
}
.lobby__key-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 7px;
  padding: 8px 0;
  font-size: 9px;
}
.lobby__key-line .muted {
  font-size: 9px;
}
.lobby__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin: 12px 0;
}
.lobby__actions .el-button {
  flex: 1;
  margin-left: 0;
}
.lobby__empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 30px 10px;
  text-align: center;
}
.lobby__empty-state span {
  font-size: 30px;
}
.lobby__empty-state p {
  margin: 0;
  font-size: 11px;
  line-height: 1.8;
  color: var(--muted);
}
.lobby__facts {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.lobby__facts li {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
  font-size: 10px;
  color: var(--muted);
}
.lobby__facts strong {
  font-weight: 500;
  color: var(--text-soft);
  text-align: right;
}
.lobby__start-note {
  margin: 14px 0 10px;
  font-size: 9px;
  line-height: 1.7;
  color: var(--muted);
}
.lobby__start {
  width: 100%;
}
.lobby__invite {
  margin-top: 14px;
  padding: 9px 10px;
  border-radius: 8px;
  border: 1px dashed var(--line);
  cursor: pointer;
}
.lobby__invite span {
  display: block;
  font-size: 8px;
  letter-spacing: 0.1em;
  color: var(--muted);
}
.lobby__invite code {
  display: block;
  margin-top: 4px;
  font-size: 9px;
  color: var(--text-soft);
  word-break: break-all;
}
.lobby__chat-card {
  padding-bottom: 14px;
}
.lobby__chat-note {
  margin: 8px 0 0;
  font-size: 8px;
  line-height: 1.6;
  color: var(--muted);
}
@media (max-width: 1280px) {
  .lobby {
    grid-template-columns: 1fr;
  }
  .lobby__side {
    position: static;
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
}
@media (max-width: 1000px) {
  .lobby__grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 760px) {
  .lobby__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .lobby__side {
    grid-template-columns: 1fr;
  }
  .lobby__header {
    flex-direction: column;
  }
}
@media (max-width: 460px) {
  .lobby__grid {
    grid-template-columns: 1fr;
  }
}
</style>
