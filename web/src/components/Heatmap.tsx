import type { Grid, Zone } from '../api'
import { hourLabel } from '../time'

interface Props {
  grid: Grid | null
  zones: Zone[]
  focus: [number, number]
}

export function Heatmap({ grid, zones, focus }: Props) {
  if (!grid) return <div className="panel empty">Loading the ChronoGrid&hellip;</div>
  const max = Math.max(1, ...Object.values(grid.counts).flat())
  const byId = Object.fromEntries(zones.map((z) => [z.id, z]))
  return (
    <div className="panel heatmap">
      <div className="panel-title">
        <span>ChronoGrid</span>
        <small>activity by zone &times; hour &middot; arrows to move &middot; OK to rewind</small>
      </div>
      <div className="grid" style={{ gridTemplateColumns: `220px repeat(${grid.hours.length}, 1fr)` }}>
        <div />
        {grid.hours.map((h) => (
          <div key={h} className="hour">
            {hourLabel(h)}
          </div>
        ))}
        {grid.zones.map((zid, r) => {
          const zone = byId[zid]
          return [
            <div key={zid} className="zone-label">
              <span className={`dot ${zone?.presence.present ? 'on' : ''}`} />
              <div>
                <div>{zone?.name ?? zid}</div>
                <small>{zone ? `${zone.objects.length} items` : ''}</small>
              </div>
            </div>,
            ...grid.counts[zid].map((n, c) => {
              const focused = focus[0] === r && focus[1] === c
              const level = n === 0 ? 0 : 0.18 + 0.82 * (n / max)
              return (
                <div
                  key={`${zid}-${c}`}
                  className={`cell ${focused ? 'focused' : ''}`}
                  style={{ ['--level' as string]: level }}
                  title={`${n} events`}
                >
                  {n > 0 ? n : ''}
                </div>
              )
            }),
          ]
        })}
      </div>
    </div>
  )
}
