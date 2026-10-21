import type { Rule } from '../api'
import { clock } from '../time'

export function DiffView({ data }: { data: any }) {
  const base = data.base
  return (
    <div className="panel diff">
      <div className="panel-title">
        <span>git diff &middot; {data.zone_name}</span>
        <small>{base ? `vs ${base.kind === 'commit' ? `commit #${base.id} "${base.message}"` : 'earlier'} at ${clock(base.ts)}` : 'no commit yet'}</small>
      </div>
      <pre className="code">
        <div className="meta">
          diff --chrono a/{data.zone_id}@{base ? clock(base.ts) : '-'} b/{data.zone_id}@now
        </div>
        {data.removed?.map((r: any) => (
          <div key={`-${r.label}`} className="del">
            - {r.label}
            {r.now_in_name ? <span className="note">  # now in {r.now_in_name}</span> : <span className="note">  # not seen since</span>}
          </div>
        ))}
        {data.added?.map((a: string) => (
          <div key={`+${a}`} className="add">
            + {a}
          </div>
        ))}
        {data.unchanged?.map((u: string) => (
          <div key={` ${u}`} className="same">
            {'  '}
            {u}
          </div>
        ))}
        {!data.removed?.length && !data.added?.length && <div className="same">  # working tree clean</div>}
      </pre>
      <p className="say">{data.say}</p>
    </div>
  )
}

export function StatusView({ data }: { data: any }) {
  return (
    <div className="panel status">
      <div className="panel-title">
        <span>git status</span>
        <small>what is where, right now</small>
      </div>
      <div className="zone-cards">
        {data.zones.map((z: any) => (
          <div key={z.zone_id} className={`zone-card ${z.uncommitted ? 'dirty' : ''}`}>
            <div className="zone-card-head">
              <span className={`dot ${z.person_present ? 'on' : ''}`} />
              {z.zone_name}
              {z.uncommitted && <span className="badge">modified</span>}
            </div>
            <ul>
              {z.objects.length ? z.objects.map((o: string) => <li key={o}>{o}</li>) : <li className="muted">empty</li>}
            </ul>
          </div>
        ))}
      </div>
      {data.appliances_on?.length > 0 && (
        <div className="appliances">
          {data.appliances_on.map((a: any) => (
            <span key={a.label} className="badge warn">
              {a.label} on since {a.on_since}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export function CommitView({ data }: { data: any }) {
  return (
    <div className="panel commit">
      <div className="panel-title">
        <span>git commit &middot; {data.zone_name}</span>
        <small>known-good layout saved</small>
      </div>
      <pre className="code">
        <div className="meta">
          [main #{data.id}] {data.message}
        </div>
        <div className="same"> {data.objects.length} objects tracked at {clock(data.ts)}</div>
        {data.objects.map((o: string) => (
          <div key={o} className="add">
            + {o}
          </div>
        ))}
      </pre>
      <p className="say">{data.say}</p>
    </div>
  )
}

function describe(cond: Record<string, any>): string {
  switch (cond.type) {
    case 'appliance_on':
      return `${cond.appliance} is on${cond.for_seconds ? ` for ${cond.for_seconds}s` : ''}`
    case 'person_absent':
      return `nobody at ${cond.zone} for ${cond.for_seconds}s`
    case 'object_missing':
      return `${cond.object} is not in ${cond.zone}`
    case 'object_present':
      return `${cond.object} is in ${cond.zone}`
    case 'time_window':
      return `time is between ${cond.start} and ${cond.end}`
    case 'sequence_not_followed':
      return `${cond.first.kind} ${cond.first.label ?? ''} not followed by ${cond.then.kind} ${cond.then.label ?? ''} within ${cond.within_seconds}s`
    default:
      return cond.type
  }
}

export function RulePR({ rule, focus }: { rule: Rule; focus: 0 | 1 }) {
  const spec = rule.spec
  return (
    <div className="panel rule-pr">
      <div className="panel-title">
        <span>
          Lint rule PR #{rule.id} &middot; {spec.name}
        </span>
        <small className={`status ${rule.status}`}>{rule.status}</small>
      </div>
      {rule.source_text && <blockquote>&ldquo;{rule.source_text}&rdquo;</blockquote>}
      <div className="rule-body">
        <div>
          <h4>Fires when all of these hold</h4>
          <ul className="conds">
            {spec.when.map((c, i) => (
              <li key={i}>{describe(c)}</li>
            ))}
          </ul>
          <h4>Then say</h4>
          <p className="say">{spec.message}</p>
          <small className="muted">
            severity {spec.severity} &middot; cooldown {spec.cooldown_seconds}s &middot; compiled by Bedrock, enforced deterministically
          </small>
        </div>
        <pre className="code small">{JSON.stringify(spec.when, null, 2)}</pre>
      </div>
      {rule.status === 'proposed' && (
        <div className="actions">
          <button className={focus === 0 ? 'focused primary' : 'primary'}>Approve &amp; enforce</button>
          <button className={focus === 1 ? 'focused' : ''}>Reject</button>
        </div>
      )}
    </div>
  )
}
