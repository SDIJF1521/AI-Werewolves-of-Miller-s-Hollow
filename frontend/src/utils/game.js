export const PHASES = {
  lobby: { label: '候场', hint: '等待房主开局', tone: 'muted' },
  idle: { label: '准备', hint: '正在发牌', tone: 'muted' },
  night_council: { label: '夜间密谈', hint: '先和 AI 对齐今夜行动', tone: 'night' },
  night: { label: '夜晚', hint: 'AI 正在行动', tone: 'night' },
  dawn: { label: '天亮', hint: '公布昨夜死讯', tone: 'dawn' },
  council: { label: '80 秒密聊', hint: '读板 · 写策略 · 提交锁定', tone: 'gold' },
  speech: { label: 'AI 发言', hint: 'AI 正在组织语言', tone: 'gold' },
  special: { label: '技能结算', hint: '白天技能发动', tone: 'violet' },
  vote_advice: { label: '锁票建议', hint: '最后 30 秒影响投票', tone: 'gold' },
  vote_reveal: { label: '投票', hint: '票型公开', tone: 'red' },
  last_words: { label: '遗言', hint: '出局 AI 的最后发言', tone: 'muted' },
  finished: { label: '复盘', hint: '身份公开 · AI 心路', tone: 'green' },
}

export const ROLE_NAMES = {
  werewolf: '狼人',
  wolf_king: '狼王',
  white_wolf_king: '白狼王',
  seer: '预言家',
  witch: '女巫',
  hunter: '猎人',
  guard: '守卫',
  idiot: '白痴',
  knight: '骑士',
  villager: '平民',
}

export const CLAIM_NAMES = {
  seer: '跳预言家',
  witch: '跳女巫',
  hunter: '跳猎人',
  guard: '跳守卫',
  idiot: '跳白痴',
  knight: '跳骑士',
  villager: '认民',
  none: '',
}

export const POSTURES = [
  { value: '冲锋', label: '冲锋', hint: '强站边，主动压人' },
  { value: '倒钩', label: '倒钩', hint: '反向站边，藏真实意图' },
  { value: '划水', label: '划水', hint: '降低存在感，保命' },
  { value: '表水', label: '表水', hint: '解释视角，争取信任' },
  { value: '悍跳', label: '悍跳', hint: '硬跳身份，制造对跳' },
]

export const LIE_LEVELS = [
  { value: '禁止', label: '禁止', hint: '尽量说真话' },
  { value: '轻度', label: '轻度', hint: '可以模糊、省略' },
  { value: '重度', label: '重度', hint: '允许编造身份与信息' },
]

export const FEEDBACK = {
  full: { label: '完全采纳', tone: 'full', icon: '✓' },
  partial: { label: '部分采纳', tone: 'partial', icon: '≈' },
  misunderstood: { label: '误解指令', tone: 'mis', icon: '?' },
  defy: { label: '抗命', tone: 'defy', icon: '✕' },
  auto: { label: '自主决策', tone: 'auto', icon: '·' },
}

export function phaseInfo(phase) {
  return PHASES[phase] || PHASES.idle
}

export function roleName(role) {
  return ROLE_NAMES[role] || role || '未知'
}

export function claimName(claim) {
  return CLAIM_NAMES[claim] || ''
}

export function feedbackInfo(kind) {
  return FEEDBACK[kind] || FEEDBACK.auto
}

export function campLabel(camp) {
  return camp === 'wolf' ? '狼人阵营' : camp === 'good' ? '好人阵营' : '未知'
}

export function campTone(camp) {
  return camp === 'wolf' ? 'wolf' : 'good'
}

export function formatClock(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export function pct(value) {
  return `${Math.round((Number(value) || 0) * 100)}%`
}

export function seatText(seat) {
  return seat ? `${seat} 号` : '—'
}

export function sortedSeats(players) {
  return (players || []).filter((p) => p.alive).sort((a, b) => a.seat - b.seat)
}

export function teamBySeat(teams, seat) {
  return (teams || []).find((t) => t.seat === seat) || null
}
