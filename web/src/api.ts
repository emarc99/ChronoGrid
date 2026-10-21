import { useEffect, useRef } from 'react'

export type BBox = [number, number, number, number]

export interface LedgerEvent {
  id: number
  ts: number
  kind: 'placed' | 'moved' | 'removed'
  label: string
  zone_id: string | null
  zone_name: string
  from_zone: string | null
  bbox: BBox | null
  clip_url: string | null
}

export interface Zone {
  id: string
  name: string
  kind: string
  objects: string[]
  presence: { present: boolean; since: number | null }
  last_commit: { id: number; ts: number; message: string; objects: Record<string, unknown> } | null
}

export interface Alert {
  id: number
  ts: number
  rule_id: number
  severity: 'info' | 'warning' | 'critical'
  title: string
  body: string
  status: 'open' | 'snoozed' | 'resolved'
  evidence: string[]
}

export interface Rule {
  id: number
  created: number
  status: 'proposed' | 'active' | 'rejected' | 'disabled'
  source_text: string | null
  spec: {
    name: string
    message: string
    severity: string
    cooldown_seconds: number
    when: Array<Record<string, unknown> & { type: string }>
  }
}

export interface Appliance {
  label: string
  zone_id: string | null
  on: boolean
  since: number
}

export interface State {
  zones: Zone[]
  appliances: Appliance[]
  alerts: Alert[]
  rules: Rule[]
  recent: LedgerEvent[]
  now: number
}

export interface Grid {
  hours: number[]
  zones: string[]
  counts: Record<string, number[]>
}

export interface ToolCall {
  tool: string
  input: Record<string, unknown>
}

export type ScreenMessage =
  | { type: 'hello' }
  | { type: 'screen'; view: 'rewind' | 'log' | 'status' | 'diff' | 'commit' | 'rule_pr'; data: any }
  | { type: 'alert' | 'alert_resolved' | 'alert_snoozed'; alert: Alert }
  | { type: 'rule_updated'; rule: Rule }
  | { type: 'event'; event: LedgerEvent }
  | { type: 'appliance'; appliance: Appliance }
  | { type: 'utterance'; text: string }
  | { type: 'assistant'; text: string; reply: string; tools: ToolCall[]; latency_ms?: number; model?: string; error?: string }

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.json() as Promise<T>
}

export const api = {
  state: () => fetch('/api/state').then(json<State>),
  grid: (hours = 12) => fetch(`/api/grid?hours=${hours}`).then(json<Grid>),
  events: (params: Record<string, string | number>) =>
    fetch('/api/events?' + new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)]))).then(
      json<LedgerEvent[]>,
    ),
  ask: (text: string) =>
    fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) }).then(
      json<{ reply: string; tools: ToolCall[]; latency_ms?: number }>,
    ),
  ruleAction: (id: number, action: 'approve' | 'reject') =>
    fetch(`/api/rules/${id}/${action}`, { method: 'POST' }).then(json<Rule>),
  snooze: (id: number, minutes = 10) => fetch(`/api/alerts/${id}/snooze?minutes=${minutes}`, { method: 'POST' }).then(json<Alert>),
  appliance: (label: string, on: boolean, zone_id = 'workbench') =>
    fetch('/api/appliance', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ label, on, zone_id }) }).then(
      json<Appliance>,
    ),
}

export function useScreenSocket(onMessage: (msg: ScreenMessage) => void, onStatus: (up: boolean) => void) {
  const handler = useRef(onMessage)
  const status = useRef(onStatus)
  handler.current = onMessage
  status.current = onStatus

  useEffect(() => {
    let ws: WebSocket | null = null
    let retry: number | undefined
    let closed = false
    const connect = () => {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      ws = new WebSocket(`${proto}://${location.host}/ws`)
      ws.onopen = () => status.current(true)
      ws.onmessage = (e) => handler.current(JSON.parse(e.data))
      ws.onclose = () => {
        status.current(false)
        if (!closed) retry = window.setTimeout(connect, 1500)
      }
    }
    connect()
    return () => {
      closed = true
      window.clearTimeout(retry)
      ws?.close()
    }
  }, [])
}
