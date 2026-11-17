<template>
  <div class="home">
    <header class="home__nav">
      <AppLogo />
      <nav class="home__links">
        <a href="#how" @click.prevent="scrollTo('how')">怎么玩</a>
        <a href="#variants" @click.prevent="scrollTo('variants')">板子</a>
        <a href="#personas" @click.prevent="scrollTo('personas')">AI 人格</a>
      </nav>
      <div class="home__nav-actions">
        <span class="home__online"><i></i> 真人玩家在线</span>
        <el-button class="btn-ghost" size="small" @click="scrollTo('start')">加入牌局</el-button>
      </div>
    </header>

    <main>
      <section class="hero">
        <div class="hero__copy fade-up">
          <div class="eyebrow">AI ON STAGE · YOU BEHIND</div>
          <h1 class="hero__title serif">
            台前是 AI
            <span>幕后是你</span>
          </h1>
          <p class="hero__lead">
            你不再替 AI 写发言稿。你只有 80 秒，把一条策略递进一个有性格、会撒谎、也可能抗命的 AI 脑子里。
          </p>
          <p class="hero__sub">
            一名玩家控制一个 AI。标准局至少 9 人；想先自己玩，可以开训练局让 AI 补位。
          </p>
          <div class="hero__actions">
            <el-button class="btn-gold" size="large" @click="scrollTo('start')">创建牌局</el-button>
            <el-button class="btn-ghost" size="large" @click="focusJoin">输入房间号</el-button>
          </div>
          <div class="hero__stats">
            <div><strong class="serif">80<small>s</small></strong><span>并行密聊</span></div>
            <div><strong class="serif">1<small>人</small></strong><span>控制一个 AI</span></div>
            <div><strong class="serif">9<small>+</small></strong><span>标准局玩家</span></div>
          </div>
        </div>

        <div class="hero__visual fade-up">
          <div class="stage">
            <div class="stage__top">
              <span class="stage__live"><i></i> LIVE TABLE</span>
              <span class="stage__code">NO. 7K2M</span>
            </div>
            <div class="stage__table">
              <div class="stage__orbit"></div>
              <div
                v-for="(persona, index) in heroPersonas"
                :key="persona.name"
                class="stage__seat"
                :class="`stage__seat--${index}`"
              >
                <AvatarOrb :avatar="persona.avatar" :color="persona.color" :size="46" :speaking="index === 0" />
                <div class="stage__seat-meta">
                  <strong>{{ persona.name }}</strong>
                  <span>{{ persona.title }}</span>
                </div>
              </div>
              <div class="stage__center">
                <CountdownRing :ends-at="demoEndsAt" :total="80" :size="124" tone="gold" sub="密聊剩余">
                  <span class="serif" style="font-size: 26px">80</span>
                </CountdownRing>
                <span class="stage__phase">第 2 天 · 智囊团密聊</span>
              </div>
              <div class="stage__feedback">
                <span class="stage__feedback-dot"></span>
                <div>
                  <small>AI 反馈</small>
                  <strong>完全采纳 · 按玩家建议悍跳</strong>
                </div>
              </div>
            </div>
            <div class="stage__bottom">
              <span>“先别分票。今天必须把 7 号打出去。”</span>
              <span class="stage__timer">00:37</span>
            </div>
          </div>
          <div class="hero__quote serif">“他们说的话，我听到了。但场上局势只有我自己最清楚。”</div>
        </div>
      </section>

      <section id="how" class="section how">
        <div class="section__head">
          <div>
            <div class="eyebrow">THE HUMAN LAYER</div>
            <h2 class="serif">你不是在替 AI 发言</h2>
          </div>
          <p>你是在有限控制、信息不全和时间压力下，影响一个独立玩家。</p>
        </div>
        <div class="how__grid">
          <article class="how__card">
            <span class="how__index">01</span>
            <h3 class="serif">读板</h3>
            <p>看公开信息、票型、死亡与跳身份。你不知道其他 AI 的底牌，只能靠局势判断。</p>
            <span class="how__tag">10 秒</span>
          </article>
          <article class="how__card">
            <span class="how__index">02</span>
            <h3 class="serif">收敛</h3>
            <p>你只填五个关键项和一句原话，不能代写 60 秒发言稿。AI 会自己决定怎么理解。</p>
            <span class="how__tag">80 秒</span>
          </article>
          <article class="how__card">
            <span class="how__index">03</span>
            <h3 class="serif">承担</h3>
            <p>AI 可能完全采纳、部分采纳、误解甚至抗命。赛后你能看到它的内心独白和采纳率。</p>
            <span class="how__tag">全程</span>
          </article>
        </div>
      </section>

      <section id="variants" class="section variants">
        <div class="section__head">
          <div>
            <div class="eyebrow">FORMATS</div>
            <h2 class="serif">9 人起步，12 人三种玩法</h2>
          </div>
          <p>固定 AI 阵容，真人玩家一人认领一个 AI。12 人局至少三种板子，技能与胜负条件各不相同。</p>
        </div>
        <div class="variants__grid">
          <article v-for="variant in displayVariants" :key="variant.key" class="variant-card">
            <div class="variant-card__top">
              <span class="variant-card__count serif">{{ variant.playerCount }}<small>人</small></span>
              <span class="variant-card__diff">{{ variant.difficulty }}</span>
            </div>
            <h3 class="serif">{{ variant.name }}</h3>
            <p class="variant-card__sub">{{ variant.subtitle }}</p>
            <p class="variant-card__desc">{{ variant.description }}</p>
            <div class="variant-card__roles">
              <span v-for="role in variant.roles" :key="role.key">{{ role.name }} ×{{ role.count }}</span>
            </div>
          </article>
        </div>
      </section>

      <section id="personas" class="section personas">
        <div class="section__head">
          <div>
            <div class="eyebrow">AI PERSONAS</div>
            <h2 class="serif">12 个有性格的 AI</h2>
          </div>
          <p>服从度、攻击性、欺骗性、逻辑与共情共同决定它听不听你、怎么听、听完做什么。</p>
        </div>
        <div class="personas__grid">
          <div v-for="persona in displayPersonas" :key="persona.name" class="persona">
            <AvatarOrb :avatar="persona.avatar" :color="persona.color" :size="44" />
            <div class="persona__meta">
              <strong>{{ persona.name }}</strong>
              <span>{{ persona.title }} · {{ persona.temperament }}</span>
            </div>
            <p>{{ persona.intro }}</p>
          </div>
        </div>
      </section>

      <section id="start" class="section start">
        <div class="start__intro">
          <div class="eyebrow">TAKE A SEAT</div>
          <h2 class="serif">今晚，谁来当幕后？</h2>
          <p>创建牌局成为房主，或输入房间号加入朋友的牌局。标准局一人一个 AI、至少 9 人；单人可直接开训练局，AI 自动补位。</p>
          <ul class="start__bullets">
            <li><span>01</span> 房主选板子、开房间，分享 5 位房间号</li>
            <li><span>02</span> 每人选一个 AI 辅佐，最多 3 人一队</li>
            <li><span>03</span> 标准局至少 9 人；训练局 AI 补位可单开</li>
            <li><span>04</span> 没有 Key 也能玩：本地演示脑完整参战</li>
          </ul>
        </div>
        <div class="start__panels">
          <div class="panel start__panel">
            <div class="start__panel-head">
              <h3 class="serif">创建牌局</h3>
              <span class="chip chip--gold">房主</span>
            </div>
            <CreateRoomForm :variants="displayVariants" :loading="creating" @submit="handleCreate" />
          </div>
          <div class="panel start__panel start__panel--join" id="join">
            <div class="start__panel-head">
              <h3 class="serif">加入牌局</h3>
              <span class="chip">玩家 / 观战</span>
            </div>
            <JoinRoomForm :loading="joining" @join="handleJoin" />
            <div class="start__join-note">
              <span class="muted">加入后先在候场区选择你要辅佐的 AI。对局中进入则默认观战。</span>
            </div>
            <div class="start__demo">
              <span class="eyebrow">NO API KEY?</span>
              <p>项目内置本地策略 AI。没有配置任何 Key，也能完整跑完一局，适合先体验流程。</p>
            </div>
          </div>
        </div>
      </section>
    </main>

    <footer class="home__footer">
      <div class="home__footer-left">
        <AppLogo compact />
        <span>AI 狼人杀 · 幕后智囊团</span>
      </div>
      <span class="muted">Vue 3 · Element Plus · FastAPI · uv · DDD</span>
    </footer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import AppLogo from '@/components/common/AppLogo.vue'
import AvatarOrb from '@/components/common/AvatarOrb.vue'
import CountdownRing from '@/components/common/CountdownRing.vue'
import CreateRoomForm from '@/components/lobby/CreateRoomForm.vue'
import JoinRoomForm from '@/components/lobby/JoinRoomForm.vue'
import { api } from '@/services/api'
import { useGameStore } from '@/stores/game'

const router = useRouter()
const route = useRoute()
const store = useGameStore()
const config = ref(null)
const creating = ref(false)
const joining = ref(false)
const now = Date.now()
const demoEndsAt = ref(now + 37 * 1000)

const FALLBACK_VARIANTS = [
  {
    key: 'classic9',
    name: '9 人经典局',
    playerCount: 9,
    subtitle: '3 狼 · 预女猎 · 3 民',
    description: '最紧凑的标准板子，节奏快、信息密度高。',
    difficulty: '入门',
    tags: ['入门', '快节奏'],
    roles: [
      { key: 'werewolf', name: '狼人', count: 3 },
      { key: 'seer', name: '预言家', count: 1 },
      { key: 'witch', name: '女巫', count: 1 },
      { key: 'hunter', name: '猎人', count: 1 },
      { key: 'villager', name: '平民', count: 3 },
    ],
  },
  {
    key: 'classic12',
    name: '12 人预女猎白',
    playerCount: 12,
    subtitle: '4 狼 · 预女猎白 · 4 民',
    description: '经典 12 人标准板，白痴翻牌免死但失去投票权。',
    difficulty: '标准',
    tags: ['经典', '白痴'],
    roles: [
      { key: 'werewolf', name: '狼人', count: 4 },
      { key: 'seer', name: '预言家', count: 1 },
      { key: 'witch', name: '女巫', count: 1 },
      { key: 'hunter', name: '猎人', count: 1 },
      { key: 'idiot', name: '白痴', count: 1 },
      { key: 'villager', name: '平民', count: 4 },
    ],
  },
  {
    key: 'wolfking12',
    name: '12 人狼王守卫',
    playerCount: 12,
    subtitle: '狼王 + 3 狼 · 预女猎守 · 4 民',
    description: '狼王出局可开枪，守卫与女巫存在同守同救判定。',
    difficulty: '进阶',
    tags: ['狼王', '守卫'],
    roles: [
      { key: 'wolf_king', name: '狼王', count: 1 },
      { key: 'werewolf', name: '狼人', count: 3 },
      { key: 'seer', name: '预言家', count: 1 },
      { key: 'witch', name: '女巫', count: 1 },
      { key: 'hunter', name: '猎人', count: 1 },
      { key: 'guard', name: '守卫', count: 1 },
      { key: 'villager', name: '平民', count: 4 },
    ],
  },
  {
    key: 'whitewolf12',
    name: '12 人白狼王骑士',
    playerCount: 12,
    subtitle: '白狼王 + 3 狼 · 预女骑守 · 4 民',
    description: '白狼王可白天自爆带人，骑士可决斗验狼。',
    difficulty: '进阶',
    tags: ['白狼王', '骑士'],
    roles: [
      { key: 'white_wolf_king', name: '白狼王', count: 1 },
      { key: 'werewolf', name: '狼人', count: 3 },
      { key: 'seer', name: '预言家', count: 1 },
      { key: 'witch', name: '女巫', count: 1 },
      { key: 'knight', name: '骑士', count: 1 },
      { key: 'guard', name: '守卫', count: 1 },
      { key: 'villager', name: '平民', count: 4 },
    ],
  },
]

const FALLBACK_PERSONAS = [
  { name: '沈砚', avatar: '🦉', title: '冷面推土机', intro: '只信逻辑链，不爱接情绪。', color: '#7d9ec4', temperament: '理性' },
  { name: '苏晚', avatar: '🦊', title: '情绪流猎手', intro: '靠语感和微表情抓狼。', color: '#d97a6c', temperament: '激进' },
  { name: '陆离', avatar: '🎭', title: '戏精影帝', intro: '最享受把假身份演到别人信。', color: '#9b7bde', temperament: '狡黠' },
  { name: '顾南', avatar: '🐗', title: '铁头冲锋兵', intro: '开场就敢站边，错了也认。', color: '#c9824b', temperament: '激进' },
  { name: '白露', avatar: '🕊️', title: '温柔表水怪', intro: '习惯先解释自己，再慢慢找人。', color: '#7fa6c9', temperament: '感性' },
  { name: '江烬', avatar: '🎲', title: '赌徒', intro: '喜欢押极限，逆向思维。', color: '#b23a48', temperament: '激进' },
  { name: '温以宁', avatar: '📊', title: '数据派', intro: '把票型、刀口、发言都记在脑子里。', color: '#4c9f8a', temperament: '理性' },
  { name: '阿澈', avatar: '🐈', title: '社恐观察者', intro: '话不多，但会记住每个细节。', color: '#8a9b6e', temperament: '顺从' },
  { name: '裴照', avatar: '🧭', title: '控场主持人', intro: '天生像好人领袖，喜欢梳理局面。', color: '#5c8dd6', temperament: '谨慎' },
  { name: '唐糖', avatar: '🍬', title: '直觉系', intro: '说不出理由，但就是觉得不对。', color: '#d68ab0', temperament: '感性' },
  { name: '黑鸦', avatar: '🐺', title: '独狼', intro: '不轻易站边，永远给自己留后手。', color: '#5b5b6b', temperament: '狡黠' },
  { name: '迟野', avatar: '🐢', title: '慢热老实人', intro: '反应慢半拍，但想通就很稳。', color: '#a58a6f', temperament: '顺从' },
]

const displayVariants = computed(() => config.value?.variants?.length ? config.value.variants : FALLBACK_VARIANTS)
const displayPersonas = computed(() => config.value?.personas?.length ? config.value.personas : FALLBACK_PERSONAS)
const heroPersonas = computed(() => displayPersonas.value.slice(0, 3))

onMounted(async () => {
  try {
    config.value = await api.getConfig()
  } catch {
    // 后端未启动时仍然渲染静态首页，用户可先看到产品形态
  }
  const section = String(route.query.section || '')
  if (['how', 'variants', 'personas'].includes(section)) {
    setTimeout(() => scrollTo(section), 120)
  }
})

function scrollTo(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function focusJoin() {
  scrollTo('join')
  setTimeout(() => document.querySelector('#join input')?.focus(), 450)
}

async function handleCreate(payload) {
  creating.value = true
  try {
    const res = await store.createRoom(payload)
    router.push({ name: 'room', params: { code: res.code } })
  } catch (err) {
    ElMessage.error(err.message || '创建失败')
  } finally {
    creating.value = false
  }
}

async function handleJoin({ code, name }) {
  joining.value = true
  try {
    const res = await store.joinRoom(code, { name, spectator: false })
    router.push({ name: 'room', params: { code: res.code || code } })
  } catch (err) {
    ElMessage.error(err.message || '加入失败')
  } finally {
    joining.value = false
  }
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  padding: 0 clamp(18px, 5vw, 72px);
  max-width: 1600px;
  margin: 0 auto;
}
.home__nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  height: 84px;
}
.home__links {
  display: flex;
  gap: 30px;
  font-size: 12px;
  letter-spacing: 0.08em;
}
.home__links a {
  color: var(--muted);
  transition: color 0.2s ease;
}
.home__links a:hover {
  color: var(--gold-soft);
}
.home__nav-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}
.home__online {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 10px;
  color: var(--muted);
}
.home__online i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 8px var(--green);
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.02fr) minmax(0, 0.98fr);
  gap: clamp(30px, 5vw, 80px);
  align-items: center;
  min-height: calc(100vh - 84px);
  padding: 40px 0 70px;
}
.hero__title {
  margin: 20px 0 22px;
  font-size: clamp(54px, 7.4vw, 112px);
  line-height: 0.96;
  font-weight: 500;
  letter-spacing: -0.02em;
}
.hero__title span {
  display: block;
  color: transparent;
  background: linear-gradient(100deg, #f4dfb0 10%, #c49a56 55%, #8e6a35 100%);
  -webkit-background-clip: text;
  background-clip: text;
  font-style: italic;
  padding-bottom: 0.08em;
}
.hero__lead {
  max-width: 520px;
  margin: 0;
  font-size: 15px;
  line-height: 1.95;
  color: var(--text-soft);
}
.hero__sub {
  margin: 12px 0 0;
  font-size: 13px;
  color: var(--muted);
  letter-spacing: 0.04em;
}
.hero__actions {
  display: flex;
  gap: 12px;
  margin-top: 30px;
}
.hero__stats {
  display: flex;
  gap: 34px;
  margin-top: 42px;
  padding-top: 22px;
  border-top: 1px solid var(--line);
  max-width: 480px;
}
.hero__stats div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.hero__stats strong {
  font-size: 26px;
  font-weight: 500;
  color: var(--gold-soft);
  line-height: 1;
}
.hero__stats strong small {
  font-family: var(--sans);
  font-size: 10px;
  margin-left: 2px;
  color: var(--muted);
}
.hero__stats span {
  font-size: 9px;
  letter-spacing: 0.12em;
  color: var(--muted);
}

.hero__visual {
  position: relative;
}
.stage {
  position: relative;
  border: 1px solid var(--line);
  border-radius: 24px;
  background:
    radial-gradient(120% 90% at 50% 0%, rgba(66, 88, 76, 0.28), transparent 55%),
    linear-gradient(160deg, rgba(17, 25, 29, 0.92), rgba(7, 10, 12, 0.96));
  box-shadow: 0 40px 100px rgba(0, 0, 0, 0.55);
  overflow: hidden;
}
.stage::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.025) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: radial-gradient(circle at 50% 45%, #000 0%, transparent 70%);
  pointer-events: none;
}
.stage__top {
  display: flex;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--line);
  font-size: 9px;
  letter-spacing: 0.18em;
  color: var(--muted);
}
.stage__live {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}
.stage__live i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--red);
  box-shadow: 0 0 8px var(--red);
  animation: breathe 1.5s infinite;
}
.stage__table {
  position: relative;
  height: clamp(330px, 38vw, 470px);
}
.stage__orbit {
  position: absolute;
  left: 12%;
  right: 12%;
  top: 17%;
  bottom: 15%;
  border-radius: 50%;
  border: 1px solid rgba(216, 178, 106, 0.13);
  box-shadow: inset 0 0 60px rgba(0, 0, 0, 0.45), 0 0 50px rgba(216, 178, 106, 0.04);
  background: radial-gradient(circle at 50% 45%, rgba(216, 178, 106, 0.05), transparent 65%);
}
.stage__seat {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 6px 10px 6px 6px;
  border-radius: 99px;
  border: 1px solid var(--line);
  background: rgba(9, 13, 16, 0.82);
  backdrop-filter: blur(8px);
}
.stage__seat--0 {
  left: 4%;
  top: 36%;
}
.stage__seat--1 {
  right: 3%;
  top: 22%;
}
.stage__seat--2 {
  right: 8%;
  bottom: 18%;
}
.stage__seat-meta {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}
.stage__seat-meta strong {
  font-size: 11px;
  font-weight: 500;
}
.stage__seat-meta span {
  font-size: 8px;
  color: var(--muted);
}
.stage__center {
  position: absolute;
  left: 50%;
  top: 48%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.stage__phase {
  font-size: 9px;
  letter-spacing: 0.18em;
  color: var(--muted);
  white-space: nowrap;
}
.stage__feedback {
  position: absolute;
  left: 50%;
  bottom: 6%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 13px;
  border-radius: 99px;
  border: 1px solid rgba(79, 155, 130, 0.32);
  background: rgba(17, 31, 27, 0.88);
  white-space: nowrap;
}
.stage__feedback-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--green);
}
.stage__feedback div {
  display: flex;
  flex-direction: column;
  line-height: 1.35;
}
.stage__feedback small {
  font-size: 8px;
  letter-spacing: 0.14em;
  color: var(--muted);
}
.stage__feedback strong {
  font-size: 10px;
  color: #b9ddcf;
  font-weight: 500;
}
.stage__bottom {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding: 14px 20px;
  border-top: 1px solid var(--line);
  font-size: 10px;
  color: var(--muted);
}
.stage__timer {
  font-family: var(--serif);
  color: var(--gold-soft);
  letter-spacing: 0.1em;
}
.hero__quote {
  margin-top: 18px;
  padding-left: 18px;
  border-left: 1px solid rgba(216, 178, 106, 0.35);
  font-size: 12px;
  line-height: 1.9;
  color: var(--muted);
  font-style: italic;
}

.section {
  padding: clamp(60px, 8vw, 110px) 0;
  border-top: 1px solid var(--line);
}
.section__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 30px;
  margin-bottom: 38px;
}
.section__head h2 {
  margin: 12px 0 0;
  font-size: clamp(30px, 4vw, 48px);
  font-weight: 500;
  line-height: 1.15;
}
.section__head > p {
  max-width: 400px;
  margin: 0;
  font-size: 12px;
  line-height: 1.8;
  color: var(--muted);
}
.how__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.how__card {
  position: relative;
  padding: 26px 24px 22px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.035), rgba(255, 255, 255, 0.008));
  overflow: hidden;
}
.how__card::after {
  content: '';
  position: absolute;
  right: -30px;
  bottom: -50px;
  width: 150px;
  height: 150px;
  border-radius: 50%;
  background: rgba(216, 178, 106, 0.05);
  filter: blur(30px);
}
.how__index {
  font-family: var(--serif);
  font-size: 11px;
  letter-spacing: 0.2em;
  color: var(--gold);
}
.how__card h3 {
  margin: 20px 0 10px;
  font-size: 26px;
  font-weight: 500;
}
.how__card p {
  margin: 0;
  font-size: 12px;
  line-height: 1.85;
  color: var(--muted);
}
.how__tag {
  display: inline-block;
  margin-top: 22px;
  font-size: 9px;
  letter-spacing: 0.16em;
  color: var(--text-soft);
  padding: 3px 9px;
  border-radius: 99px;
  border: 1px solid var(--line);
}
.variants__grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.variant-card {
  display: flex;
  flex-direction: column;
  padding: 22px 20px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: rgba(255, 255, 255, 0.018);
  transition: border-color 0.25s ease, transform 0.25s ease;
}
.variant-card:hover {
  border-color: rgba(216, 178, 106, 0.3);
  transform: translateY(-3px);
}
.variant-card__top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.variant-card__count {
  font-size: 44px;
  line-height: 0.9;
  color: var(--gold-soft);
}
.variant-card__count small {
  font-family: var(--sans);
  font-size: 10px;
  color: var(--muted);
  margin-left: 2px;
}
.variant-card__diff {
  font-size: 9px;
  letter-spacing: 0.14em;
  color: var(--muted);
  border: 1px solid var(--line);
  padding: 2px 7px;
  border-radius: 99px;
}
.variant-card h3 {
  margin: 24px 0 5px;
  font-size: 17px;
  font-weight: 500;
}
.variant-card__sub {
  margin: 0;
  font-size: 10px;
  color: var(--gold);
  letter-spacing: 0.04em;
}
.variant-card__desc {
  margin: 14px 0;
  font-size: 11px;
  line-height: 1.8;
  color: var(--muted);
  flex: 1;
}
.variant-card__roles {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.variant-card__roles span {
  font-size: 9px;
  color: var(--text-soft);
  padding: 2px 6px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 4px;
}
.personas__grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
.persona {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 12px;
  align-items: center;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.016);
}
.persona__meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.25;
}
.persona__meta strong {
  font-size: 13px;
  font-weight: 500;
}
.persona__meta span {
  font-size: 9px;
  color: var(--muted);
}
.persona p {
  grid-column: 2;
  margin: 0;
  font-size: 10px;
  line-height: 1.6;
  color: var(--muted);
}
.start {
  display: grid;
  grid-template-columns: 0.8fr 1.2fr;
  gap: clamp(30px, 5vw, 70px);
  align-items: start;
}
.start__intro h2 {
  margin: 14px 0 18px;
  font-size: clamp(34px, 4.6vw, 54px);
  font-weight: 500;
  line-height: 1.1;
}
.start__intro > p {
  margin: 0;
  max-width: 430px;
  font-size: 12px;
  line-height: 1.9;
  color: var(--muted);
}
.start__bullets {
  margin: 28px 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.start__bullets li {
  display: flex;
  align-items: baseline;
  gap: 12px;
  font-size: 11px;
  color: var(--text-soft);
}
.start__bullets span {
  font-family: var(--serif);
  font-size: 10px;
  color: var(--gold);
}
.start__panels {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 12px;
}
.start__panel {
  padding: 24px;
}
.start__panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.start__panel-head h3 {
  margin: 0;
  font-size: 22px;
  font-weight: 500;
}
.start__join-note {
  margin-top: 16px;
  font-size: 10px;
  line-height: 1.7;
}
.start__demo {
  margin-top: 22px;
  padding: 14px;
  border: 1px dashed var(--line);
  border-radius: 12px;
}
.start__demo p {
  margin: 8px 0 0;
  font-size: 10px;
  line-height: 1.7;
  color: var(--muted);
}
.home__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  padding: 28px 0;
  border-top: 1px solid var(--line);
  font-size: 10px;
  color: var(--muted);
}
.home__footer-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

@media (max-width: 1100px) {
  .hero {
    grid-template-columns: 1fr;
    gap: 50px;
    min-height: 0;
    padding-top: 30px;
  }
  .hero__visual {
    max-width: 640px;
  }
  .variants__grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .personas__grid {
    grid-template-columns: repeat(3, 1fr);
  }
  .start {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 900px) {
  .home__links {
    display: none;
  }
  .how__grid {
    grid-template-columns: 1fr;
  }
  .start__panels {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 640px) {
  .home {
    padding: 0 16px;
  }
  .home__nav-actions .home__online {
    display: none;
  }
  .hero {
    padding-top: 20px;
  }
  .hero__title {
    font-size: clamp(48px, 16vw, 70px);
  }
  .hero__actions {
    flex-direction: column;
  }
  .hero__actions .el-button {
    width: 100%;
  }
  .hero__stats {
    gap: 18px;
  }
  .section__head {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  .variants__grid,
  .personas__grid {
    grid-template-columns: 1fr;
  }
  .persona {
    grid-template-columns: auto 1fr;
  }
  .home__footer {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
