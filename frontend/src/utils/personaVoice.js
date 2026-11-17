/**
 * AI 人格 → 浏览器语音参数。
 *
 * 不依赖特定云 TTS：用 Web Speech API 的中文音色 + 音高/语速/音量，
 * 让每个 AI 的说话方式尽量贴近设定。不同系统可用的中文音色不同，
 * 因此 hints 只做优先级匹配，找不到时回退到第一个中文音色。
 */
export const PERSONA_VOICE_PROFILES = {
  沈砚: {
    pitch: 0.86,
    rate: 0.96,
    volume: 1,
    hints: ['yunxi', '云希', 'yunjian', '云健', 'kangkang', '康康'],
    label: '冷峻低音 · 克制',
  },
  苏晚: {
    pitch: 1.16,
    rate: 1.08,
    volume: 1,
    hints: ['xiaoxiao', '晓晓', 'xiaoyi', '晓伊', 'xiaomo'],
    label: '明亮偏高 · 情绪流',
  },
  陆离: {
    pitch: 1.02,
    rate: 0.93,
    volume: 1,
    hints: ['yunjian', '云健', 'yunxi', '云希', 'xiaoxiao'],
    label: '戏剧化 · 慢半拍',
  },
  顾南: {
    pitch: 0.97,
    rate: 1.16,
    volume: 1,
    hints: ['yunyang', '云扬', 'yunxi', '云希', 'kangkang'],
    label: '直给 · 快节奏',
  },
  白露: {
    pitch: 1.1,
    rate: 0.9,
    volume: 0.95,
    hints: ['xiaoxiao', '晓晓', 'xiaoyi', '晓伊', 'huihui', '慧慧'],
    label: '柔和偏轻 · 慢',
  },
  江烬: {
    pitch: 1.03,
    rate: 1.06,
    volume: 1,
    hints: ['yunxi', '云希', 'yunjian', '云健', 'xiaoxiao'],
    label: '轻佻 · 起伏',
  },
  温以宁: {
    pitch: 0.94,
    rate: 1,
    volume: 1,
    hints: ['xiaoxiao', '晓晓', 'xiaoyi', '晓伊', 'yunjian'],
    label: '冷静 · 平稳',
  },
  阿澈: {
    pitch: 0.9,
    rate: 0.84,
    volume: 0.9,
    hints: ['yunxi', '云希', 'yunjian', '云健', 'kangkang'],
    label: '低声 · 迟疑',
  },
  裴照: {
    pitch: 0.98,
    rate: 1.01,
    volume: 1,
    hints: ['yunjian', '云健', 'yunxi', '云希', 'xiaoxiao'],
    label: '稳重 · 控场',
  },
  唐糖: {
    pitch: 1.2,
    rate: 1.13,
    volume: 1,
    hints: ['xiaoyi', '晓伊', 'xiaoxiao', '晓晓', 'huihui'],
    label: '跳脱 · 高音',
  },
  黑鸦: {
    pitch: 0.8,
    rate: 0.88,
    volume: 0.95,
    hints: ['yunxi', '云希', 'yunjian', '云健', 'kangkang'],
    label: '低沉 · 留白',
  },
  迟野: {
    pitch: 0.93,
    rate: 0.82,
    volume: 0.95,
    hints: ['yunxi', '云希', 'yunjian', '云健', 'kangkang'],
    label: '慢热 · 温和',
  },
}

const DEFAULT_PROFILE = {
  pitch: 1,
  rate: 1,
  volume: 1,
  hints: [],
  label: '标准中文音色',
}

export function voiceProfileFor(name) {
  return PERSONA_VOICE_PROFILES[name] || DEFAULT_PROFILE
}
