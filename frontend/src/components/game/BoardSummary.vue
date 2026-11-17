<template>
  <div class="board">
    <div class="board__section">
      <div class="board__head">
        <span>昨夜 / 死讯</span>
        <small>{{ game?.day ? `第 ${game.day} 天` : '未开始' }}</small>
      </div>
      <div v-if="deaths.length" class="board__deaths">
        <span v-for="death in deaths.slice(-6)" :key="`${death.day}-${death.seat}`" class="board__death">
          <b>{{ death.seat }}</b>{{ death.name }}<i>D{{ death.day }}</i>
        </span>
      </div>
      <p v-else class="board__empty">暂无死讯。平安夜，或者还没天亮。</p>
    </div>

    <div class="board__section">
      <div class="board__head">
        <span>公开跳身份</span>
        <small>{{ claims.length }} 条</small>
      </div>
      <div v-if="claims.length" class="board__claims">
        <span v-for="claim in claims" :key="claim.seat" class="board__claim">
          <b>{{ claim.seat }}</b>{{ claim.name }}
          <em>{{ claim.roleName }}</em>
        </span>
      </div>
      <p v-else class="board__empty">还没有人公开身份。</p>
    </div>

    <div class="board__section">
      <div class="board__head">
        <span>最近票型</span>
        <small>{{ lastVote ? `第 ${lastVote.day} 天` : '—' }}</small>
      </div>
      <template v-if="lastVote">
        <div class="board__votes">
          <span v-for="vote in lastVote.votes" :key="vote.from" class="board__vote">
            {{ vote.from }}<i>→</i>{{ vote.to || '弃票' }}
          </span>
        </div>
        <div class="board__result">
          {{ lastVote.tie ? '平票，无人出局' : lastVote.exile ? `${lastVote.exile} 号被放逐` : '无人出局' }}
        </div>
      </template>
      <p v-else class="board__empty">第一轮还没有投票记录。</p>
    </div>

    <div v-if="lastWords" class="board__section">
      <div class="board__head"><span>遗言</span><small>{{ lastWords.seat }} 号</small></div>
      <p class="board__last">{{ lastWords.text }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  game: { type: Object, default: null },
})

const deaths = computed(() => props.game?.board?.deaths || [])
const claims = computed(() => props.game?.board?.claims || [])
const lastVote = computed(() => {
  const votes = props.game?.board?.votes || []
  return votes[votes.length - 1] || null
})
const lastWords = computed(() => {
  const list = props.game?.board?.lastWords || []
  return list[list.length - 1] || null
})
</script>

<style scoped>
.board {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.board__section {
  padding-bottom: 12px;
  border-bottom: 1px solid var(--line);
}
.board__section:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.board__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 8px;
}
.board__head span {
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--text-soft);
}
.board__head small {
  font-size: 8px;
  color: var(--muted);
}
.board__deaths,
.board__claims,
.board__votes {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.board__death,
.board__claim,
.board__vote {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 7px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--line);
  font-size: 9px;
  color: var(--text-soft);
}
.board__death b,
.board__claim b {
  font-family: var(--serif);
  color: var(--gold);
  font-weight: 500;
}
.board__death i {
  font-style: normal;
  color: var(--muted);
  font-size: 7px;
}
.board__claim em {
  font-style: normal;
  color: var(--gold-soft);
}
.board__vote i {
  font-style: normal;
  color: var(--red);
}
.board__result {
  margin-top: 7px;
  font-size: 9px;
  color: var(--muted);
}
.board__empty {
  margin: 0;
  font-size: 9px;
  line-height: 1.7;
  color: var(--muted);
}
.board__last {
  margin: 0;
  font-size: 10px;
  line-height: 1.8;
  color: var(--text-soft);
  font-style: italic;
}
</style>
