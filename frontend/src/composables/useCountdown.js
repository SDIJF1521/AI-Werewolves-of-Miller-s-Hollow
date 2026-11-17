import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

export function useCountdown(endsAt, totalSeconds = null, offset = null) {
  const now = ref(Date.now())
  let timer = null

  onMounted(() => {
    timer = window.setInterval(() => {
      now.value = Date.now()
    }, 200)
  })

  onBeforeUnmount(() => {
    if (timer) window.clearInterval(timer)
  })

  const remaining = computed(() => {
    const target = Number(endsAt?.value ?? endsAt ?? 0)
    if (!target) return 0
    const skew = Number(offset?.value ?? offset ?? 0)
    return Math.max(0, target - (now.value + skew))
  })

  const seconds = computed(() => Math.ceil(remaining.value / 1000))
  const label = computed(() => {
    const s = seconds.value
    return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
  })
  const totalMs = computed(() => {
    const total = Number(totalSeconds?.value ?? totalSeconds ?? 0)
    return total > 0 ? total * 1000 : Math.max(remaining.value, 1)
  })
  const progress = computed(() => Math.min(1, Math.max(0, remaining.value / totalMs.value)))
  const urgent = computed(() => seconds.value > 0 && seconds.value <= 10)

  return { remaining, seconds, label, progress, urgent, totalMs }
}
