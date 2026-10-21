// Simulated Alexa+ audio: browser speech recognition in, Amazon Polly (via /api/tts) out.

type Recognition = {
  lang: string
  interimResults: boolean
  continuous: boolean
  onresult: ((e: any) => void) | null
  onend: (() => void) | null
  onerror: ((e: any) => void) | null
  start: () => void
  stop: () => void
}

export function speechSupported(): boolean {
  return Boolean((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition)
}

export function listen(onPartial: (text: string) => void, onFinal: (text: string) => void): () => void {
  const Ctor = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  if (!Ctor) return () => {}
  const rec: Recognition = new Ctor()
  rec.lang = 'en-US'
  rec.interimResults = true
  rec.continuous = true
  let finalText = ''
  let latest = ''
  rec.onresult = (e: any) => {
    let interim = ''
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const r = e.results[i]
      if (r.isFinal) finalText += r[0].transcript
      else interim += r[0].transcript
    }
    latest = (finalText + ' ' + interim).trim()
    onPartial(latest)
  }
  rec.onend = () => {
    if (latest) onFinal(latest)
  }
  rec.onerror = () => {}
  rec.start()
  return () => rec.stop()
}

let current: HTMLAudioElement | null = null

export function speak(text: string): Promise<void> {
  current?.pause()
  const audio = new Audio(`/api/tts?text=${encodeURIComponent(text)}`)
  current = audio
  return new Promise((resolve) => {
    audio.onended = () => resolve()
    audio.onerror = () => resolve()
    audio.play().catch(() => resolve())
  })
}

let ctx: AudioContext | null = null

export function chime(kind: 'alert' | 'listen' | 'ok' = 'ok') {
  ctx ??= new AudioContext()
  const notes = kind === 'alert' ? [880, 660, 880] : kind === 'listen' ? [523, 784] : [784, 1046]
  notes.forEach((freq, i) => {
    const osc = ctx!.createOscillator()
    const gain = ctx!.createGain()
    const t = ctx!.currentTime + i * 0.13
    osc.frequency.value = freq
    osc.type = 'sine'
    gain.gain.setValueAtTime(0.0001, t)
    gain.gain.exponentialRampToValueAtTime(0.25, t + 0.02)
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.12)
    osc.connect(gain).connect(ctx!.destination)
    osc.start(t)
    osc.stop(t + 0.13)
  })
}
