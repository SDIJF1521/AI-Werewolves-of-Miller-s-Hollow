<template>
  <el-dialog
    :model-value="modelValue"
    title="配置 AI 大脑"
    width="min(520px, 92vw)"
    align-center
    @update:model-value="$emit('update:modelValue', $event)"
    @open="load"
  >
    <div class="key-dialog">
      <div class="key-dialog__notice">
        <span class="key-dialog__icon">KEY</span>
        <div>
          <strong>你是该 AI 的唯一玩家</strong>
          <p>绑定后该 AI 的发言走 LLM；Key 只保存在服务端内存，不会广播给其他玩家。刷新页面或重启服务后需要重新填写。</p>
        </div>
      </div>

      <div v-if="existing?.hasKey" class="key-dialog__existing">
        <div>
          <span class="muted">当前绑定</span>
          <strong>{{ existing.model }}</strong>
          <small>{{ existing.maskedKey }} · {{ existing.provider }}</small>
        </div>
        <el-button class="btn-danger-ghost" size="small" @click="remove">移除</el-button>
      </div>

      <el-form label-position="top" class="key-dialog__form">
        <div class="key-dialog__row">
          <el-form-item label="服务商">
            <el-select v-model="form.provider" @change="onProvider">
              <el-option v-for="p in providers" :key="p.key" :label="p.name" :value="p.key" />
            </el-select>
          </el-form-item>
          <el-form-item label="模型">
            <el-input v-model="form.model" placeholder="deepseek-chat" />
          </el-form-item>
        </div>
        <el-form-item label="API Base URL">
          <el-input v-model="form.baseUrl" placeholder="https://api.deepseek.com/v1" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="form.apiKey" type="password" show-password placeholder="sk-..." autocomplete="off" />
        </el-form-item>
      </el-form>

      <div v-if="testResult" class="key-dialog__result" :class="{ 'key-dialog__result--ok': testOk }">
        {{ testResult }}
      </div>

      <div class="key-dialog__actions">
        <el-button class="btn-ghost" :loading="testing" @click="test">测试连接</el-button>
        <el-button class="btn-gold" :loading="saving" @click="save">保存并绑定</el-button>
      </div>
      <p class="key-dialog__foot">
        没有 Key 也可以开局：该 AI 会使用本地演示脑，仍有性格、发言、投票和抗命。
      </p>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/services/api'
import { useGameStore } from '@/stores/game'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  room: { type: Object, required: true },
  teamSeat: { type: Number, default: null },
})
const emit = defineEmits(['update:modelValue', 'saved'])
const store = useGameStore()

const providers = ref([])
const form = reactive({ provider: 'deepseek', baseUrl: '', model: '', apiKey: '' })
const testing = ref(false)
const saving = ref(false)
const testResult = ref('')
const testOk = ref(false)

const team = computed(() => props.room?.teams?.find((t) => t.seat === props.teamSeat) || null)
const existing = computed(() => team.value?.key || null)

async function load() {
  testResult.value = ''
  try {
    const config = await api.getConfig()
    providers.value = config.providers || []
    if (!form.baseUrl) onProvider(form.provider)
  } catch {
    providers.value = [{ key: 'deepseek', name: 'DeepSeek', baseUrl: 'https://api.deepseek.com/v1', defaultModel: 'deepseek-chat' }]
    onProvider(form.provider)
  }
  if (existing.value?.hasKey) {
    form.provider = existing.value.provider || form.provider
    form.baseUrl = existing.value.baseUrl || form.baseUrl
    form.model = existing.value.model || form.model
  }
}

function onProvider(key) {
  const provider = providers.value.find((p) => p.key === key)
  if (!provider) return
  form.baseUrl = provider.baseUrl || ''
  form.model = provider.defaultModel || ''
}

async function test() {
  if (!form.apiKey) {
    ElMessage.warning('先填 API Key')
    return
  }
  testing.value = true
  testResult.value = ''
  try {
    const res = await api.testKey(form)
    testOk.value = true
    testResult.value = `连接成功：${res.reply || 'OK'}（${res.model}）`
  } catch (err) {
    testOk.value = false
    testResult.value = err.message || '连接失败'
  } finally {
    testing.value = false
  }
}

async function save() {
  if (!form.apiKey && !existing.value?.hasKey) {
    ElMessage.warning('请填写 API Key')
    return
  }
  saving.value = true
  try {
    await api.setKey(props.room.code, store.session, form)
    ElMessage.success('已绑定 AI 大脑，该 AI 将使用 LLM 发言')
    emit('saved')
    emit('update:modelValue', false)
  } catch (err) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function remove() {
  try {
    await api.deleteKey(props.room.code, store.session, props.teamSeat)
    ElMessage.success('已移除 Key，该 AI 将使用演示脑')
    emit('saved')
  } catch (err) {
    ElMessage.error(err.message || '移除失败')
  }
}
</script>

<style scoped>
.key-dialog {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.key-dialog__notice {
  display: flex;
  gap: 12px;
  padding: 12px;
  border: 1px solid rgba(216, 178, 106, 0.2);
  border-radius: 12px;
  background: rgba(216, 178, 106, 0.05);
}
.key-dialog__icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex: none;
  border-radius: 8px;
  border: 1px solid rgba(216, 178, 106, 0.35);
  font-size: 8px;
  letter-spacing: 0.1em;
  color: var(--gold-soft);
}
.key-dialog__notice strong {
  display: block;
  font-size: 12px;
  color: var(--gold-soft);
}
.key-dialog__notice p {
  margin: 4px 0 0;
  font-size: 10px;
  line-height: 1.7;
  color: var(--muted);
}
.key-dialog__existing {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
}
.key-dialog__existing div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.key-dialog__existing strong {
  font-size: 12px;
}
.key-dialog__existing small {
  font-size: 9px;
  color: var(--muted);
}
.key-dialog__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.key-dialog__form :deep(.el-form-item) {
  margin-bottom: 12px;
}
.key-dialog__result {
  font-size: 10px;
  color: #e7a39b;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid rgba(198, 90, 79, 0.25);
  background: rgba(198, 90, 79, 0.06);
}
.key-dialog__result--ok {
  color: #a8d6c4;
  border-color: rgba(79, 155, 130, 0.3);
  background: rgba(79, 155, 130, 0.06);
}
.key-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.key-dialog__foot {
  margin: 0;
  font-size: 9px;
  line-height: 1.7;
  color: var(--muted);
}
@media (max-width: 520px) {
  .key-dialog__row {
    grid-template-columns: 1fr;
  }
}
</style>
