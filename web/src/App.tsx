import { useCallback, useEffect, useRef, useState } from 'react'
import { api, useScreenSocket, type Alert, type Grid, type LedgerEvent, type Rule, type ScreenMessage, type State } from './api'
import { AlexaPanel, type Turn } from './components/AlexaPanel'
import { Heatmap } from './components/Heatmap'
import { Hud, Ticker } from './components/Hud'
import { RewindHost } from './components/RewindHost'
import { CommitView, DiffView, RulePR, StatusView } from './components/Views'
import { ago, clock } from './time'
import { chime, listen, speak } from './voice'

type View =
  | { kind: 'home' }
  | { kind: 'rewind'; data: any }
  | { kind: 'diff'; data: any }
  | { kind: 'status'; data: any }
  | { kind: 'commit'; data: any }
  | { kind: 'rule_pr'; rule: Rule }

const IDLE_MS = 60_000

function toHistory(e: LedgerEvent) {
  return { ...e, time_text: clock(e.ts), ago_text: ago(e.ts) }
}

export default function App() {
  const [state, setState] = useState<State | null>(null)
  const [grid, setGrid] = useState<Grid | null>(null)
  const [connected, setConnected] = useState(false)
  const [view, setView] = useState<View>({ kind: 'home' })
  const [focus, setFocus] = useState<[number, number]>([0, 11])
  const [prFocus, setPrFocus] = useState<0 | 1>(0)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [turns, setTurns] = useState<Turn[]>([])
  const [listening, setListening] = useState(false)
  const [partial, setPartial] = useState('')
  const [thinking, setThinking] = useState(false)
  const [model, setModel] = useState<string>()
  const [now, setNow] = useState(Date.now())
  const stopListening = useRef<(() => void) | null>(null)
  const lastInteraction = useRef(Date.now())
  const turnId = useRef(0)

  const refresh = useCallback(async () => {
    const [s, g] = await Promise.all([api.state(), api.grid(12)])
    setState(s)
    setGrid(g)
    setAlerts(s.alerts)
  }, [])

  useEffect(() => {
    refresh()
    const t = setInterval(() => {
      setNow(Date.now())
      if (Date.now() - lastInteraction.current > IDLE_MS) setView((v) => (v.kind === 'home' ? v : { kind: 'home' }))
    }, 5000)
    const g = setInterval(refresh, 30_000)
    return () => {
      clearInterval(t)
      clearInterval(g)
    }
  }, [refresh])

  const show = (v: View) => {
    lastInteraction.current = Date.now()
    setView(v)
  }

  const addTurn = (t: Omit<Turn, 'id'>) => setTurns((prev) => [...prev, { ...t, id: ++turnId.current }])

  const onMessage = useCallback(
    (msg: ScreenMessage) => {
      switch (msg.type) {
        case 'screen':
          if (msg.view === 'rewind') show({ kind: 'rewind', data: msg.data })
          else if (msg.view === 'diff') show({ kind: 'diff', data: msg.data })
          else if (msg.view === 'status') show({ kind: 'status', data: msg.data })
          else if (msg.view === 'commit') show({ kind: 'commit', data: msg.data })
          else if (msg.view === 'rule_pr') {
            setPrFocus(0)
            show({ kind: 'rule_pr', rule: msg.data })
          } else if (msg.view === 'log' && msg.data.entries?.length) {
            show({ kind: 'rewind', data: { ...msg.data, ...msg.data.entries[0], history: msg.data.entries } })
          }
          break
        case 'utterance':
          addTurn({ role: 'user', text: msg.text })
          setThinking(true)
          break
        case 'assistant':
          setThinking(false)
          setModel(msg.model)
          addTurn({ role: 'alexa', text: msg.reply, tools: msg.tools, latency: msg.latency_ms })
          speak(msg.reply)
          refresh()
          break
        case 'alert':
          setAlerts((prev) => [msg.alert, ...prev.filter((a) => a.id !== msg.alert.id)])
          chime('alert')
          setTimeout(() => speak(msg.alert.body), 450)
          break
        case 'alert_resolved':
        case 'alert_snoozed':
          setAlerts((prev) => prev.filter((a) => a.id !== msg.alert.id))
          break
        case 'rule_updated':
          setView((v) => (v.kind === 'rule_pr' && v.rule.id === msg.rule.id ? { kind: 'rule_pr', rule: msg.rule } : v))
          if (msg.rule.status === 'active') chime('ok')
          setTimeout(() => setView((v) => (v.kind === 'rule_pr' && v.rule.status !== 'proposed' ? { kind: 'home' } : v)), 3500)
          refresh()
          break
        case 'event':
        case 'appliance':
          refresh()
          break
      }
    },
    [refresh],
  )

  useScreenSocket(onMessage, setConnected)

  const ask = useCallback((text: string) => {
    lastInteraction.current = Date.now()
    api.ask(text).catch(() => setThinking(false))
  }, [])

  const startListening = useCallback(() => {
    if (stopListening.current) return
    chime('listen')
    setListening(true)
    setPartial('')
    stopListening.current = listen(setPartial, (finalText) => {
      setListening(false)
      setPartial('')
      ask(finalText)
    })
  }, [ask])

  const endListening = useCallback(() => {
    stopListening.current?.()
    stopListening.current = null
    setListening(false)
  }, [])

  const openCell = useCallback(
    async (r: number, c: number) => {
      if (!grid) return
      const zone_id = grid.zones[r]
      const since = grid.hours[c]
      const events = await api.events({ zone_id, since, until: since + 3600, limit: 20 })
      const pick = events.find((e) => e.kind !== 'removed') ?? events[0]
      if (!pick) return
      const history = (await api.events({ label: pick.label, limit: 6 })).map(toHistory)
      const current = history.find((h) => h.id === pick.id) ?? toHistory(pick)
      show({
        kind: 'rewind',
        data: { found: true, object: pick.label, ...current, history: [current, ...history.filter((h) => h.id !== current.id)] },
      })
    },
    [grid],
  )

  const decidePR = useCallback(async (rule: Rule, choice: 0 | 1) => {
    await api.ruleAction(rule.id, choice === 0 ? 'approve' : 'reject')
  }, [])

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      lastInteraction.current = Date.now()
      const typing = (e.target as HTMLElement)?.tagName === 'INPUT'
      if (typing) {
        if (e.key === 'Escape') (e.target as HTMLElement).blur()
        return
      }
      if (e.code === 'Space') {
        e.preventDefault()
        if (!e.repeat) startListening()
        return
      }
      if (e.key === 's' || e.key === 'S') {
        const open = alerts.find((a) => a.status === 'open')
        if (open) api.snooze(open.id)
        return
      }
      if (e.key === 'h' || e.key === 'H') {
        const iron = state?.appliances.find((a) => a.label === 'soldering iron')
        api.appliance('soldering iron', !iron?.on)
        return
      }
      if (view.kind === 'home' && grid) {
        const rows = grid.zones.length
        const cols = grid.hours.length
        if (e.key === 'ArrowUp') setFocus(([r, c]) => [Math.max(0, r - 1), c])
        else if (e.key === 'ArrowDown') setFocus(([r, c]) => [Math.min(rows - 1, r + 1), c])
        else if (e.key === 'ArrowLeft') setFocus(([r, c]) => [r, Math.max(0, c - 1)])
        else if (e.key === 'ArrowRight') setFocus(([r, c]) => [r, Math.min(cols - 1, c + 1)])
        else if (e.key === 'Enter') openCell(focus[0], focus[1])
        else return
        e.preventDefault()
        return
      }
      if (view.kind === 'rule_pr' && view.rule.status === 'proposed') {
        if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') setPrFocus((f) => (f === 0 ? 1 : 0))
        else if (e.key === 'Enter') decidePR(view.rule, prFocus)
        else if (e.key === 'Escape' || e.key === 'Backspace') show({ kind: 'home' })
        return
      }
      if (e.key === 'Escape' || e.key === 'Backspace') show({ kind: 'home' })
    }
    const up = (e: KeyboardEvent) => {
      if (e.code === 'Space' && (e.target as HTMLElement)?.tagName !== 'INPUT') endListening()
    }
    window.addEventListener('keydown', down)
    window.addEventListener('keyup', up)
    return () => {
      window.removeEventListener('keydown', down)
      window.removeEventListener('keyup', up)
    }
  }, [view, grid, focus, prFocus, alerts, state, startListening, endListening, openCell, decidePR])

  const appliancesOn = state?.appliances.filter((a) => a.on) ?? []
  const activeRules = state?.rules.filter((r) => r.status === 'active').length ?? 0

  return (
    <div className="screen">
      <header className="top">
        <div className="brand">
          <span className="logo">&#9638;</span> ChronoGrid
          <small>git for the physical world</small>
        </div>
        <div className="top-right">
          {appliancesOn.map((a) => (
            <span key={a.label} className="badge warn">
              {a.label} on
            </span>
          ))}
          <span className="badge">{activeRules} lint rules active</span>
          <span className={`conn ${connected ? 'up' : ''}`}>{connected ? 'live' : 'offline'}</span>
          <span className="clock">{new Date(now).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</span>
        </div>
      </header>

      <main className="stage">
        {view.kind === 'home' && <Heatmap grid={grid} zones={state?.zones ?? []} focus={focus} />}
        {view.kind === 'rewind' && <RewindHost data={view.data} onClose={() => show({ kind: 'home' })} />}
        {view.kind === 'diff' && <DiffView data={view.data} />}
        {view.kind === 'status' && <StatusView data={view.data} />}
        {view.kind === 'commit' && <CommitView data={view.data} />}
        {view.kind === 'rule_pr' && <RulePR rule={view.rule} focus={prFocus} />}
      </main>

      <AlexaPanel
        turns={turns}
        listening={listening}
        partial={partial}
        thinking={thinking}
        model={model}
        onSubmit={ask}
        onMic={() => (listening ? endListening() : startListening())}
      />

      <Hud alerts={alerts} onSnooze={(id) => api.snooze(id)} />
      <Ticker events={state?.recent ?? []} />
    </div>
  )
}
