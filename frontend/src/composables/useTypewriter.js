import { onBeforeUnmount, ref, watch } from 'vue'

export function useTypewriter(textRef, speed = 22) {
  const display = ref('')
  const done = ref(false)
  let timer = null
  let source = ''

  function stop() {
    if (timer) {
      window.clearTimeout(timer)
      timer = null
    }
  }

  function play(text) {
    stop()
    source = text || ''
    display.value = ''
    done.value = false
    if (!source) {
      done.value = true
      return
    }
    let index = 0
    const tick = () => {
      const step = source.length > 260 ? 3 : source.length > 120 ? 2 : 1
      index = Math.min(source.length, index + step)
      display.value = source.slice(0, index)
      if (index >= source.length) {
        done.value = true
        timer = null
        return
      }
      timer = window.setTimeout(tick, speed)
    }
    tick()
  }

  watch(
    () => textRef.value,
    (text) => {
      if ((text || '') === source) return
      play(text || '')
    },
    { immediate: true },
  )

  function skip() {
    if (!done.value) {
      stop()
      display.value = source
      done.value = true
    }
  }

  onBeforeUnmount(stop)

  return { display, done, skip, replay: () => play(source) }
}
