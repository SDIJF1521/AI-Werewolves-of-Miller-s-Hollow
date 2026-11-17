<template>
  <div class="night-order">
    <div class="night-order__head">
      <div>
        <span class="eyebrow">NIGHT COUNCIL</span>
        <h3 class="serif">夜间行动密谈</h3>
      </div>
      <span class="chip" :class="{ 'chip--green': team.nightLocked }">
        {{ team.nightLocked ? '已锁定' : '等待指令' }}
      </span>
    </div>

    <div v-if="!privateInfo?.you?.alive" class="night-order__locked">
      <div class="night-order__locked-title">你的 AI 已出局</div>
      <p>本夜没有行动。你可以继续观战，等待下一局。</p>
    </div>

    <div v-else-if="team.nightLocked" class="night-order__locked">
      <div class="night-order__locked-title">本夜指令已提交</div>
      <p>{{ orderSummary }}</p>
      <blockquote v-if="team.nightOrder?.directive">“{{ team.nightOrder.directive }}”</blockquote>
      <p class="night-order__wait">等待 AI 行动。它可能完全执行，也可能按自己的判断改线。</p>
    </div>

    <template v-else>
      <div class="night-order__role">
        <span class="chip" :class="isWolf ? 'chip--red' : 'chip--green'">{{ roleLabel }}</span>
        <span>{{ roleHint }}</span>
      </div>

      <div v-if="actionOptions.length > 1" class="night-order__actions">
        <button
          v-for="option in actionOptions"
          :key="option.value"
          type="button"
          class="night-order__action"
          :class="{ 'is-active': form.action === option.value }"
          @click="changeAction(option.value)"
        >
          <strong>{{ option.label }}</strong>
          <small>{{ option.hint }}</small>
        </button>
      </div>

      <label v-if="needsTarget" class="night-order__field">
        <span>行动目标</span>
        <SeatPicker
          v-model="form.target"
          :players="targetPlayers"
          :exclude="form.action === 'protect' ? null : you.teamSeat"
          placeholder="选择目标"
        />
      </label>

      <label class="night-order__field">
        <span>给 AI 的夜间嘱咐 <em>会进入它的行动判断</em></span>
        <el-input
          v-model="form.directive"
          type="textarea"
          :rows="2"
          maxlength="140"
          show-word-limit
          placeholder="例如：今晚优先刀 7 号；如果 7 号被守，就换 3 号。"
        />
      </label>

      <div class="night-order__buttons">
        <el-button class="btn-ghost" @click="submitAuto">让 AI 自主判断</el-button>
        <el-button class="btn-gold" @click="submit">提交夜间指令</el-button>
      </div>
      <p class="night-order__hint">AI 会参考你的嘱咐、其他 AI 的发言和此前投票；不是提线木偶。</p>
    </template>
  </div>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import SeatPicker from '@/components/common/SeatPicker.vue'

const props = defineProps({
  game: { type: Object, default: null },
  team: { type: Object, default: null },
  you: { type: Object, required: true },
  privateInfo: { type: Object, default: null },
  players: { type: Array, default: () => [] },
})
const emit = defineEmits(['submit'])

const role = computed(() => props.privateInfo?.you?.role || '')
const roleLabel = computed(() => props.privateInfo?.you?.roleName || '')
const isWolf = computed(() => props.privateInfo?.you?.camp === 'wolf')
const roleHint = computed(() => {
  if (isWolf.value) return '狼队共同选择刀口；你的建议会计入狼队决策。'
  if (role.value === 'seer') return '选择今晚查验谁，结果会在天亮后进入你的私密信息。'
  if (role.value === 'witch') return '解药会自动救被刀目标；毒药需要选择目标。一晚只能使用一瓶药。'
  if (role.value === 'guard') return '选择守护目标，不能连续两晚守同一人。'
  return '你的 AI 本夜没有主动技能，但仍可留一句战术嘱咐。'
})

const actionOptions = computed(() => {
  if (isWolf.value) return [{ value: 'kill', label: '狼刀', hint: '选择刀口' }]
  if (role.value === 'seer') return [{ value: 'check', label: '查验', hint: '选择目标' }]
  if (role.value === 'witch') {
    return [
      { value: 'save', label: '解药', hint: '救被刀目标' },
      { value: 'poison', label: '毒药', hint: '选择目标' },
      { value: 'none', label: '不用药', hint: '保留药品' },
    ]
  }
  if (role.value === 'guard') return [{ value: 'protect', label: '守护', hint: '选择目标' }]
  return []
})

const form = reactive({ action: 'auto', target: null, directive: '' })
const needsTarget = computed(() => ['kill', 'check', 'poison', 'protect'].includes(form.action))
const targetPlayers = computed(() => {
  const mates = new Set((props.privateInfo?.wolfMates || []).map((m) => m.seat))
  return props.players.filter(
    (p) =>
      p.alive &&
      (form.action === 'protect' || p.seat !== props.you.teamSeat) &&
      !(isWolf.value && mates.has(p.seat)),
  )
})

watch(
  () => `${props.game?.day || 0}-${props.team?.nightLocked}-${role.value}`,
  () => {
    if (props.team?.nightLocked) return
    form.action = actionOptions.value[0]?.value || 'auto'
    form.target = null
    form.directive = ''
  },
  { immediate: true },
)

const orderSummary = computed(() => {
  const order = props.team?.nightOrder
  if (!order) return '已提交。'
  if (order.action === 'auto') return '让 AI 按自己的判断行动。'
  const labels = { kill: '刀', check: '验', save: '救', poison: '毒', protect: '守', none: '不使用技能' }
  return `${labels[order.action] || order.action}${order.target ? ` ${order.target} 号` : ''}`
})

function changeAction(action) {
  form.action = action
  if (action === 'save' || action === 'none') form.target = null
}

function submit() {
  if (needsTarget.value && !form.target) {
    ElMessage.warning('先选择一个行动目标，或选择让 AI 自主判断')
    return
  }
  emit('submit', {
    action: form.action,
    target: form.target,
    directive: form.directive.trim(),
  })
}

function submitAuto() {
  emit('submit', { action: 'auto', target: null, directive: form.directive.trim() })
}
</script>

<style scoped>
.night-order {
  display: flex;
  flex-direction: column;
  gap: 11px;
  padding: 11px;
  border: 1px solid rgba(111, 149, 187, 0.28);
  border-radius: 11px;
  background: rgba(111, 149, 187, 0.04);
}
.night-order__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}
.night-order__head h3 {
  margin: 5px 0 0;
  font-size: 18px;
  font-weight: 500;
}
.night-order__role {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 8px;
  color: var(--muted);
}
.night-order__actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
}
.night-order__action {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 5px;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.02);
  color: var(--text-soft);
  text-align: center;
  cursor: pointer;
}
.night-order__action strong {
  font-size: 9px;
  font-weight: 500;
}
.night-order__action small {
  font-size: 7px;
  color: var(--muted);
}
.night-order__action.is-active {
  border-color: rgba(111, 149, 187, 0.55);
  background: rgba(111, 149, 187, 0.12);
  color: #c3d8ec;
}
.night-order__field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.night-order__field > span {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 8px;
  letter-spacing: 0.08em;
  color: var(--muted);
}
.night-order__field em {
  font-style: normal;
  letter-spacing: 0;
  color: rgba(111, 149, 187, 0.8);
}
.night-order__buttons {
  display: flex;
  gap: 6px;
}
.night-order__buttons .el-button {
  flex: 1;
  margin-left: 0;
}
.night-order__hint {
  margin: 0;
  font-size: 8px;
  line-height: 1.6;
  color: var(--muted);
}
.night-order__locked {
  padding: 10px;
  border-radius: 8px;
  border: 1px solid rgba(79, 155, 130, 0.25);
  background: rgba(79, 155, 130, 0.05);
}
.night-order__locked-title {
  font-size: 10px;
  color: #a8d6c4;
}
.night-order__locked p {
  margin: 5px 0;
  font-size: 9px;
  line-height: 1.65;
  color: var(--muted);
}
.night-order__locked blockquote {
  margin: 7px 0;
  padding-left: 8px;
  border-left: 2px solid rgba(216, 178, 106, 0.3);
  font-size: 9px;
  line-height: 1.6;
  color: var(--text-soft);
}
.night-order__wait {
  font-size: 8px !important;
  opacity: 0.8;
}
</style>
