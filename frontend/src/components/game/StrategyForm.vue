<template>
  <div class="strategy">
    <div class="strategy__head">
      <div>
        <span class="eyebrow">STRATEGY PACKAGE</span>
        <h3 class="serif">给 AI 的策略包</h3>
      </div>
      <div class="strategy__state">
        <span v-if="team.locked" class="chip chip--green">已锁定</span>
        <span v-else-if="isCaptain" class="chip chip--gold">你是唯一玩家</span>
        <span v-else class="chip">建议中</span>
      </div>
    </div>

    <div class="strategy__locked" v-if="team.locked">
      <div class="strategy__locked-title">本轮已锁定</div>
      <p>AI 将按加权后的策略包执行。它可能完全采纳、部分采纳、误解，甚至抗命。</p>
      <div v-if="aggregate" class="strategy__summary">
        <span>{{ aggregate.package.posture }}</span>
        <span v-if="aggregate.package.protectSeat">保 {{ aggregate.package.protectSeat }}</span>
        <span v-if="aggregate.package.attackSeat">打 {{ aggregate.package.attackSeat }}</span>
        <span v-if="aggregate.package.voteSeat">投 {{ aggregate.package.voteSeat }}</span>
        <span>{{ aggregate.package.lieLevel }}撒谎</span>
      </div>
      <blockquote v-if="aggregate?.package?.directive">“{{ aggregate.package.directive }}”</blockquote>
      <div v-if="aggregate?.contributors?.length" class="strategy__weights">
        <span v-for="c in aggregate.contributors" :key="c.memberId" class="strategy__weight">
          {{ c.name }} ×{{ c.weight }}
          <i v-if="c.hasKey">KEY</i>
          <i v-else-if="c.isCaptain">玩家</i>
        </span>
      </div>
    </div>

    <template v-else>
      <div class="strategy__field">
        <span class="strategy__label">本轮姿态</span>
        <div class="strategy__postures">
          <button
            v-for="item in POSTURES"
            :key="item.value"
            type="button"
            class="strategy__posture"
            :class="{ 'is-active': form.posture === item.value }"
            :disabled="!editable"
            @click="form.posture = item.value"
          >
            <strong>{{ item.label }}</strong>
            <small>{{ item.hint }}</small>
          </button>
        </div>
      </div>

      <div class="strategy__grid">
        <label class="strategy__field">
          <span class="strategy__label">主保</span>
          <SeatPicker v-model="form.protectSeat" :players="players" :disabled="!editable" placeholder="保谁" />
        </label>
        <label class="strategy__field">
          <span class="strategy__label">主打</span>
          <SeatPicker
            v-model="form.attackSeat"
            :players="players"
            :exclude="you.teamSeat"
            :disabled="!editable"
            placeholder="打谁"
          />
        </label>
        <label class="strategy__field">
          <span class="strategy__label">建议投票</span>
          <SeatPicker
            v-model="form.voteSeat"
            :players="players"
            :exclude="you.teamSeat"
            :disabled="!editable"
            placeholder="投谁"
          />
        </label>
        <label class="strategy__field">
          <span class="strategy__label">撒谎许可</span>
          <el-select v-model="form.lieLevel" size="small" :disabled="!editable">
            <el-option v-for="item in LIE_LEVELS" :key="item.value" :label="`${item.label} · ${item.hint}`" :value="item.value" />
          </el-select>
        </label>
      </div>

      <label class="strategy__field">
        <span class="strategy__label">
          给 AI 的原话
          <em>最终进入 AI 提示词的是你写的这句</em>
        </span>
        <el-input
          v-model="form.directive"
          type="textarea"
          :rows="3"
          maxlength="140"
          show-word-limit
          :disabled="!editable"
          placeholder="例如：今天必须归票 5 号，别分票；3 号可以保一轮，但不要和他绑定。"
        />
      </label>

      <div class="strategy__actions">
        <span class="strategy__hint">
          {{ isCaptain ? '提交后立即锁定' : '玩家提交后立即锁定' }}
        </span>
        <el-button class="btn-gold" :disabled="!editable" @click="submit">
          {{ isCaptain ? '提交并锁定' : '提交策略' }}
        </el-button>
      </div>
    </template>

    <div v-if="aggregate && !team.locked" class="strategy__live">
      <div class="strategy__live-head">
        <span>当前加权</span>
        <span>玩家方案</span>
      </div>
      <div class="strategy__summary">
        <span>{{ aggregate.package.posture }}</span>
        <span v-if="aggregate.package.protectSeat">保 {{ aggregate.package.protectSeat }}</span>
        <span v-if="aggregate.package.attackSeat">打 {{ aggregate.package.attackSeat }}</span>
        <span v-if="aggregate.package.voteSeat">投 {{ aggregate.package.voteSeat }}</span>
      </div>
      <div v-if="aggregate.contributors?.length" class="strategy__weights">
        <span v-for="c in aggregate.contributors" :key="c.memberId" class="strategy__weight">
          {{ c.name }} ×{{ c.weight }}
          <i v-if="c.hasKey">KEY</i>
          <i v-else-if="c.isCaptain">玩家</i>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import SeatPicker from '@/components/common/SeatPicker.vue'
import { LIE_LEVELS, POSTURES } from '@/utils/game'

const props = defineProps({
  game: { type: Object, default: null },
  team: { type: Object, default: null },
  players: { type: Array, default: () => [] },
  you: { type: Object, required: true },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['submit'])

const form = reactive({
  posture: '表水',
  protectSeat: null,
  attackSeat: null,
  voteSeat: null,
  lieLevel: '轻度',
  directive: '',
})

const isCaptain = computed(() => props.team?.captainId === props.you?.id)
const editable = computed(() => !props.disabled && !props.team?.locked)
const aggregate = computed(() => props.team?.aggregate || null)

function fromPackage(pkg) {
  if (!pkg) return
  form.posture = pkg.posture || '表水'
  form.protectSeat = pkg.protectSeat ?? null
  form.attackSeat = pkg.attackSeat ?? null
  form.voteSeat = pkg.voteSeat ?? null
  form.lieLevel = pkg.lieLevel || '轻度'
  form.directive = pkg.directive || ''
}

function reset() {
  const mine = props.team?.packages?.[props.you?.id]
  if (mine) {
    fromPackage(mine)
    return
  }
  const agg = props.team?.aggregate?.package
  if (agg) {
    fromPackage(agg)
    return
  }
  form.posture = '表水'
  form.protectSeat = null
  form.attackSeat = null
  form.voteSeat = null
  form.lieLevel = '轻度'
  form.directive = ''
}

watch(
  () => `${props.game?.day ?? 0}-${props.game?.phase ?? ''}-${props.team?.seat ?? ''}`,
  () => {
    if (props.game?.phase === 'council') reset()
  },
  { immediate: true },
)

function submit() {
  if (!form.directive.trim()) {
    ElMessage.warning('写一句给 AI 的原话，不能只给空策略')
    return
  }
  emit('submit', {
    posture: form.posture,
    protectSeat: form.protectSeat,
    attackSeat: form.attackSeat,
    lieLevel: form.lieLevel,
    voteSeat: form.voteSeat,
    directive: form.directive.trim(),
  })
}
</script>

<style scoped>
.strategy {
  display: flex;
  flex-direction: column;
  gap: 13px;
}
.strategy__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
}
.strategy__head h3 {
  margin: 5px 0 0;
  font-size: 20px;
  font-weight: 500;
}
.strategy__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.strategy__label {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 9px;
  letter-spacing: 0.1em;
  color: var(--muted);
}
.strategy__label em {
  font-style: normal;
  letter-spacing: 0;
  color: rgba(216, 178, 106, 0.7);
}
.strategy__postures {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 4px;
}
.strategy__posture {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 7px 4px 6px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.02);
  color: var(--text-soft);
  text-align: center;
  cursor: pointer;
}
.strategy__posture strong {
  font-size: 10px;
  font-weight: 500;
}
.strategy__posture small {
  font-size: 7px;
  line-height: 1.35;
  color: var(--muted);
}
.strategy__posture.is-active {
  border-color: rgba(216, 178, 106, 0.5);
  background: rgba(216, 178, 106, 0.1);
  color: var(--gold-soft);
}
.strategy__posture:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.strategy__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.strategy__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.strategy__hint {
  font-size: 8px;
  color: var(--muted);
}
.strategy__actions .el-button {
  flex: none;
}
.strategy__locked {
  padding: 12px;
  border-radius: 10px;
  border: 1px solid rgba(79, 155, 130, 0.25);
  background: rgba(79, 155, 130, 0.05);
}
.strategy__locked-title {
  font-size: 11px;
  font-weight: 500;
  color: #a8d6c4;
}
.strategy__locked p {
  margin: 5px 0 9px;
  font-size: 9px;
  line-height: 1.7;
  color: var(--muted);
}
.strategy__locked blockquote {
  margin: 9px 0;
  padding-left: 9px;
  border-left: 2px solid rgba(216, 178, 106, 0.35);
  font-size: 10px;
  line-height: 1.7;
  color: var(--text-soft);
}
.strategy__summary {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.strategy__summary span {
  font-size: 8px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(216, 178, 106, 0.1);
  color: var(--gold-soft);
}
.strategy__weights {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 7px;
}
.strategy__weight {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 8px;
  color: var(--muted);
}
.strategy__weight i {
  font-style: normal;
  font-size: 7px;
  color: var(--gold);
}
.strategy__live {
  padding-top: 10px;
  border-top: 1px dashed var(--line);
}
.strategy__live-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
  font-size: 8px;
  color: var(--muted);
}
@media (max-width: 420px) {
  .strategy__postures {
    grid-template-columns: repeat(3, 1fr);
  }
  .strategy__grid {
    grid-template-columns: 1fr;
  }
}
</style>
