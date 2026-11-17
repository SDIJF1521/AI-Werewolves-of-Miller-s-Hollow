<template>
  <teleport to="body">
    <transition name="review">
      <div v-if="modelValue" class="review-overlay" @click.self="$emit('close')">
        <div class="review">
          <button class="review__close" type="button" aria-label="关闭复盘" @click="$emit('close')">×</button>

          <header class="review__hero" :class="`review__hero--${winnerTone}`">
            <div class="review__hero-glow"></div>
            <div class="eyebrow">GAME REVIEW · {{ review?.days || 0 }} DAYS</div>
            <h1 class="serif">{{ winnerTitle }}</h1>
            <p>{{ review?.winReason }}</p>
            <div class="review__hero-stats">
              <div><strong>{{ review?.agents?.length || 0 }}</strong><span>AI 玩家</span></div>
              <div><strong>{{ pct(review?.adoptionRate) }}</strong><span>综合采纳率</span></div>
              <div><strong>{{ totalSpeeches }}</strong><span>段发言</span></div>
              <div><strong>{{ review?.deaths?.length || 0 }}</strong><span>出局</span></div>
            </div>
          </header>

          <div class="review__tabs">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              type="button"
              class="review__tab"
              :class="{ 'is-active': activeTab === tab.key }"
              @click="activeTab = tab.key"
            >
              {{ tab.label }}
            </button>
            <div class="review__tabs-spacer"></div>
            <el-button class="btn-ghost" size="small" @click="$emit('home')">返回首页</el-button>
            <el-button class="btn-gold" size="small" @click="$emit('close')">查看牌桌</el-button>
          </div>

          <div class="review__body">
            <template v-if="activeTab === 'report'">
              <div class="review__agents">
                <div
                  v-for="agent in agents"
                  :key="agent.seat"
                  class="review-agent"
                  :class="`review-agent--${campTone(agent.camp)}`"
                >
                  <div class="review-agent__top">
                    <span class="review-agent__seat">{{ String(agent.seat).padStart(2, '0') }}</span>
                    <AvatarOrb :avatar="agent.avatar" :color="agentColor(agent.seat)" :size="38" :alive="agent.alive" />
                    <div>
                      <strong class="serif">{{ agent.name }}</strong>
                      <span>{{ agent.title }}</span>
                    </div>
                    <span class="review-agent__role" :class="`is-${campTone(agent.camp)}`">{{ agent.roleName }}</span>
                  </div>
                  <div class="review-agent__meta">
                    <span>{{ agent.alive ? '存活' : agent.deathReason || '出局' }}</span>
                    <span>{{ agent.speechCount }} 次发言</span>
                    <span>信任 {{ pct(agent.trust) }}</span>
                  </div>
                  <div class="review-agent__bar">
                    <i :style="{ width: `${agentRate(agent) * 100}%` }"></i>
                  </div>
                  <small>采纳率 {{ pct(agentRate(agent)) }}</small>
                </div>
              </div>

              <div class="review__columns">
                <section class="review__card">
                  <h3 class="serif">出局时间线</h3>
                  <div class="review__timeline">
                    <div v-for="(death, index) in review?.deaths || []" :key="index" class="review__event">
                      <span class="review__event-day">D{{ death.day }}</span>
                      <span class="review__event-dot"></span>
                      <span>{{ death.seat }} 号 {{ death.name }}</span>
                    </div>
                    <p v-if="!review?.deaths?.length" class="review__empty">无人出局。</p>
                  </div>
                </section>
                <section class="review__card">
                  <h3 class="serif">票型记录</h3>
                  <div class="review__votes">
                    <div v-for="round in review?.votes || []" :key="round.day" class="review__vote-round">
                      <span class="review__event-day">D{{ round.day }}</span>
                      <div class="review__vote-list">
                        <span v-for="vote in round.votes" :key="vote.from">{{ vote.from }}→{{ vote.to || '弃' }}</span>
                      </div>
                      <strong>{{ round.tie ? '平票' : round.exile ? `${round.exile} 号出局` : '无人出局' }}</strong>
                    </div>
                    <p v-if="!review?.votes?.length" class="review__empty">没有投票记录。</p>
                  </div>
                </section>
              </div>
            </template>

            <template v-else-if="activeTab === 'inner'">
              <div class="review__inner-grid">
                <article v-for="agent in agents" :key="agent.seat" class="review__inner-card">
                  <header>
                    <AvatarOrb :avatar="agent.avatar" :color="agentColor(agent.seat)" :size="34" />
                    <div>
                      <strong>{{ agent.seat }} 号 {{ agent.name }}</strong>
                      <span>{{ agent.roleName }} · {{ agent.camp === 'wolf' ? '狼人阵营' : '好人阵营' }}</span>
                    </div>
                  </header>
                  <div class="review__inner-list">
                    <p v-for="(inner, index) in agent.inner" :key="index">“{{ inner }}”</p>
                    <p v-if="!agent.inner?.length" class="review__empty">这一局它没来得及发言。</p>
                  </div>
                  <footer>
                    <span v-for="(fb, index) in agent.adoptions" :key="index">
                      <FeedbackBadge :feedback="fb" compact />
                    </span>
                  </footer>
                </article>
              </div>
            </template>

            <template v-else>
              <div class="review__adoption-grid">
                <div class="review__stat">
                  <span>完全采纳</span>
                  <strong>{{ review?.adoptionCounts?.full || 0 }}</strong>
                  <p>AI 严格按策略包行动。</p>
                </div>
                <div class="review__stat">
                  <span>部分采纳</span>
                  <strong>{{ review?.adoptionCounts?.partial || 0 }}</strong>
                  <p>大方向对了，但语气或执行有偏差。</p>
                </div>
                <div class="review__stat review__stat--violet">
                  <span>误解指令</span>
                  <strong>{{ review?.adoptionCounts?.misunderstood || 0 }}</strong>
                  <p>它很自信地理解错了你的意思。</p>
                </div>
                <div class="review__stat review__stat--red">
                  <span>抗命</span>
                  <strong>{{ review?.adoptionCounts?.defy || 0 }}</strong>
                  <p>性格压过了服从，AI 临时改线。</p>
                </div>
              </div>

              <div class="review__adoption-list">
                <div v-for="agent in agents" :key="agent.seat" class="review__adoption-row">
                  <span class="review__adoption-name">{{ agent.seat }} 号 {{ agent.name }}</span>
                  <div class="review__adoption-bar">
                    <i :style="{ width: `${agentRate(agent) * 100}%` }"></i>
                  </div>
                  <span>{{ pct(agentRate(agent)) }}</span>
                  <span class="muted">{{ agent.adoptions?.length || 0 }} 轮反馈</span>
                </div>
              </div>

              <div class="review__note">
                <span class="eyebrow">DESIGN NOTE</span>
                <p>
                  采纳率不是越高越好。完全听话的 AI 缺少惊喜，完全抗命的 AI 让玩家失去意义。
                  真正的乐趣，是在“它听懂了没有”和“它会不会坑”之间反复判断。
                </p>
              </div>
            </template>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { computed, ref } from 'vue'
import AvatarOrb from '@/components/common/AvatarOrb.vue'
import FeedbackBadge from '@/components/game/FeedbackBadge.vue'
import { campTone, pct } from '@/utils/game'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  review: { type: Object, default: null },
})
defineEmits(['close', 'home'])

const activeTab = ref('report')
const tabs = [
  { key: 'report', label: '战报' },
  { key: 'inner', label: 'AI 心路' },
  { key: 'adoption', label: '采纳率' },
]

const agents = computed(() => props.review?.agents || [])
const totalSpeeches = computed(() => agents.value.reduce((sum, a) => sum + (a.speechCount || 0), 0))
const winnerTone = computed(() => (props.review?.winner === 'wolf' ? 'wolf' : 'good'))
const winnerTitle = computed(() => (props.review?.winner === 'wolf' ? '狼人阵营胜利' : '好人阵营胜利'))

function agentColor(seat) {
  return props.review?.agents?.find((a) => a.seat === seat)?.color || '#8a9b6e'
}

function agentRate(agent) {
  const list = agent.adoptions || []
  if (!list.length) return 0
  const good = list.filter((f) => ['full', 'partial'].includes(f.kind)).length
  return good / list.length
}
</script>

<style scoped>
.review-overlay {
  position: fixed;
  inset: 0;
  z-index: 2200;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 3vh 2vw;
  overflow-y: auto;
  background: rgba(3, 5, 7, 0.82);
  backdrop-filter: blur(12px);
}
.review {
  position: relative;
  width: min(1160px, 96vw);
  border: 1px solid var(--line);
  border-radius: 22px;
  background: #0d1317;
  box-shadow: 0 50px 120px rgba(0, 0, 0, 0.65);
  overflow: hidden;
}
.review__close {
  position: absolute;
  right: 18px;
  top: 14px;
  z-index: 2;
  width: 30px;
  height: 30px;
  border: 1px solid var(--line);
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.25);
  color: var(--text-soft);
  font-size: 18px;
  cursor: pointer;
}
.review__hero {
  position: relative;
  padding: 38px 38px 26px;
  border-bottom: 1px solid var(--line);
  background:
    radial-gradient(90% 140% at 15% 0%, rgba(79, 155, 130, 0.18), transparent 60%),
    radial-gradient(80% 120% at 90% 10%, rgba(216, 178, 106, 0.1), transparent 60%);
  overflow: hidden;
}
.review__hero--wolf {
  background:
    radial-gradient(90% 140% at 15% 0%, rgba(198, 90, 79, 0.2), transparent 60%),
    radial-gradient(80% 120% at 90% 10%, rgba(143, 52, 46, 0.12), transparent 60%);
}
.review__hero-glow {
  position: absolute;
  right: -80px;
  top: -100px;
  width: 300px;
  height: 300px;
  border-radius: 50%;
  background: rgba(216, 178, 106, 0.08);
  filter: blur(40px);
}
.review__hero h1 {
  margin: 14px 0 8px;
  font-size: clamp(34px, 5vw, 58px);
  font-weight: 500;
  line-height: 1.05;
}
.review__hero p {
  margin: 0;
  font-size: 11px;
  color: var(--text-soft);
}
.review__hero-stats {
  display: flex;
  gap: 40px;
  margin-top: 26px;
}
.review__hero-stats div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.review__hero-stats strong {
  font-family: var(--serif);
  font-size: 24px;
  font-weight: 500;
  color: var(--gold-soft);
}
.review__hero-stats span {
  font-size: 8px;
  letter-spacing: 0.12em;
  color: var(--muted);
}
.review__tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 20px;
  border-bottom: 1px solid var(--line);
}
.review__tab {
  padding: 7px 12px;
  border: none;
  border-bottom: 1px solid transparent;
  background: transparent;
  color: var(--muted);
  font-size: 11px;
  cursor: pointer;
}
.review__tab.is-active {
  color: var(--gold-soft);
  border-bottom-color: var(--gold);
}
.review__tabs-spacer {
  flex: 1;
}
.review__body {
  padding: 24px 28px 30px;
  max-height: 62vh;
  overflow-y: auto;
}
.review__agents {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.review-agent {
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.02);
}
.review-agent--wolf {
  border-color: rgba(198, 90, 79, 0.22);
}
.review-agent--good {
  border-color: rgba(79, 155, 130, 0.18);
}
.review-agent__top {
  display: flex;
  align-items: center;
  gap: 7px;
}
.review-agent__seat {
  font-family: var(--serif);
  font-size: 8px;
  color: var(--muted);
}
.review-agent__top div {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}
.review-agent__top strong {
  font-size: 12px;
  font-weight: 500;
}
.review-agent__top div span {
  font-size: 7px;
  color: var(--muted);
}
.review-agent__role {
  margin-left: auto;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 8px;
  border: 1px solid var(--line);
}
.review-agent__role.is-wolf {
  color: #e7a39b;
  border-color: rgba(198, 90, 79, 0.3);
}
.review-agent__role.is-good {
  color: #a8d6c4;
  border-color: rgba(79, 155, 130, 0.3);
}
.review-agent__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
  margin: 7px 0;
  font-size: 7px;
  color: var(--muted);
}
.review-agent__bar {
  height: 3px;
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.06);
  overflow: hidden;
}
.review-agent__bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--green), var(--gold));
}
.review-agent small {
  display: block;
  margin-top: 3px;
  font-size: 7px;
  color: var(--muted);
}
.review__columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 20px;
}
.review__card {
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 12px;
}
.review__card h3 {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 500;
}
.review__timeline {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.review__event {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 9px;
  color: var(--text-soft);
}
.review__event-day {
  font-family: var(--serif);
  font-size: 8px;
  color: var(--gold);
}
.review__event-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--red);
}
.review__votes {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.review__vote-round {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 8px;
  color: var(--muted);
}
.review__vote-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.review__vote-list span {
  padding: 1px 4px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-soft);
}
.review__vote-round strong {
  margin-left: auto;
  font-weight: 500;
  color: var(--gold-soft);
  white-space: nowrap;
}
.review__inner-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}
.review__inner-card {
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.018);
}
.review__inner-card header {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 9px;
}
.review__inner-card header div {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.review__inner-card header strong {
  font-size: 11px;
  font-weight: 500;
}
.review__inner-card header span {
  font-size: 8px;
  color: var(--muted);
}
.review__inner-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.review__inner-list p {
  margin: 0;
  font-size: 9px;
  line-height: 1.7;
  color: var(--text-soft);
  font-style: italic;
}
.review__inner-card footer {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  margin-top: 9px;
}
.review__adoption-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.review__stat {
  padding: 16px;
  border: 1px solid rgba(79, 155, 130, 0.22);
  border-radius: 11px;
  background: rgba(79, 155, 130, 0.04);
}
.review__stat span {
  font-size: 9px;
  color: var(--muted);
}
.review__stat strong {
  display: block;
  margin: 4px 0;
  font-family: var(--serif);
  font-size: 30px;
  font-weight: 500;
  color: #a8d6c4;
}
.review__stat p {
  margin: 0;
  font-size: 8px;
  line-height: 1.6;
  color: var(--muted);
}
.review__stat--violet {
  border-color: rgba(155, 123, 222, 0.22);
  background: rgba(155, 123, 222, 0.04);
}
.review__stat--violet strong {
  color: #cbbaf3;
}
.review__stat--red {
  border-color: rgba(198, 90, 79, 0.22);
  background: rgba(198, 90, 79, 0.04);
}
.review__stat--red strong {
  color: #e7a39b;
}
.review__adoption-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-top: 20px;
}
.review__adoption-row {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 9px;
  color: var(--text-soft);
}
.review__adoption-name {
  width: 110px;
  flex: none;
}
.review__adoption-bar {
  flex: 1;
  height: 4px;
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.05);
  overflow: hidden;
}
.review__adoption-bar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--green), var(--gold));
}
.review__adoption-row > span:nth-last-child(2) {
  width: 38px;
  text-align: right;
  font-family: var(--serif);
  color: var(--gold-soft);
}
.review__note {
  margin-top: 24px;
  padding: 16px;
  border: 1px dashed var(--line);
  border-radius: 11px;
}
.review__note p {
  margin: 8px 0 0;
  font-size: 10px;
  line-height: 1.8;
  color: var(--muted);
}
.review__empty {
  font-size: 9px;
  color: var(--muted);
}
.review-enter-active,
.review-leave-active {
  transition: opacity 0.25s ease;
}
.review-enter-from,
.review-leave-to {
  opacity: 0;
}
@media (max-width: 900px) {
  .review__agents {
    grid-template-columns: repeat(3, 1fr);
  }
  .review__adoption-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .review__inner-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 640px) {
  .review-overlay {
    padding: 0;
  }
  .review {
    width: 100%;
    border-radius: 0;
    min-height: 100vh;
  }
  .review__hero {
    padding: 30px 20px 20px;
  }
  .review__hero-stats {
    gap: 18px;
    flex-wrap: wrap;
  }
  .review__body {
    padding: 16px;
    max-height: none;
  }
  .review__agents {
    grid-template-columns: repeat(2, 1fr);
  }
  .review__columns {
    grid-template-columns: 1fr;
  }
  .review__tabs .el-button {
    display: none;
  }
}
</style>
