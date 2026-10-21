import type { Alert, LedgerEvent } from '../api'
import { ago, clock } from '../time'

export function Hud({ alerts, onSnooze }: { alerts: Alert[]; onSnooze: (id: number) => void }) {
  return (
    <div className="hud">
      {alerts
        .filter((a) => a.status === 'open')
        .map((a) => (
          <div key={a.id} className={`hud-card ${a.severity}`}>
            <div className="hud-head">
              <span className="sev">{a.severity === 'critical' ? '⚠ Hazard' : a.severity === 'warning' ? 'Heads up' : 'Reminder'}</span>
              <small>lint &middot; {a.title}</small>
            </div>
            <div className="hud-body">{a.body}</div>
            <ul className="evidence">
              {a.evidence.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
            <button onClick={() => onSnooze(a.id)}>Snooze 10 min (S)</button>
          </div>
        ))}
    </div>
  )
}

export function Ticker({ events }: { events: LedgerEvent[] }) {
  return (
    <footer className="ticker">
      <span className="ticker-label">git log</span>
      <div className="ticker-items">
        {events.slice(0, 8).map((e) => (
          <span key={e.id} className={`tick ${e.kind}`}>
            <b>{e.label}</b> {e.kind === 'removed' ? 'picked up from' : e.kind === 'moved' ? '→' : 'put in'} {e.zone_name}{' '}
            <small>
              {clock(e.ts)} &middot; {ago(e.ts)}
            </small>
          </span>
        ))}
      </div>
    </footer>
  )
}
