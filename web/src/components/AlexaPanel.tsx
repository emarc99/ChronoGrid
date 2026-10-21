import { useState } from 'react'
import type { ToolCall } from '../api'

export interface Turn {
  id: number
  role: 'user' | 'alexa'
  text: string
  tools?: ToolCall[]
  latency?: number
}

interface Props {
  turns: Turn[]
  listening: boolean
  partial: string
  thinking: boolean
  onSubmit: (text: string) => void
  onMic: () => void
  model?: string
}

function toolLabel(t: ToolCall): string {
  const args = Object.entries(t.input ?? {})
    .filter(([k]) => k !== 'rule' && k !== 'request_text')
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(', ')
  return `${t.tool}(${args})`
}

export function AlexaPanel({ turns, listening, partial, thinking, onSubmit, onMic, model }: Props) {
  const [text, setText] = useState('')
  return (
    <aside className="alexa">
      <div className="alexa-head">
        <div className={`ring ${listening ? 'listening' : thinking ? 'thinking' : ''}`} />
        <div>
          <div className="alexa-title">Alexa+</div>
          <small>ChronoGrid MCP &middot; Strands on Amazon Bedrock{model ? ` · ${model.replace(/^us\./, '')}` : ''}</small>
        </div>
      </div>
      <div className="turns">
        {turns.slice(-8).map((t) => (
          <div key={t.id} className={`turn ${t.role}`}>
            <div className="bubble">{t.text}</div>
            {t.tools && t.tools.length > 0 && (
              <div className="tools">
                {t.tools.map((tool, i) => (
                  <code key={i}>mcp &rarr; {toolLabel(tool)}</code>
                ))}
                {t.latency ? <small>{(t.latency / 1000).toFixed(1)}s</small> : null}
              </div>
            )}
          </div>
        ))}
        {listening && <div className="turn user live">{partial || 'Listening…'}</div>}
        {thinking && <div className="turn alexa live">&hellip;</div>}
      </div>
      <form
        className="ask"
        onSubmit={(e) => {
          e.preventDefault()
          if (text.trim()) onSubmit(text.trim())
          setText('')
        }}
      >
        <button type="button" className={`mic ${listening ? 'on' : ''}`} onClick={onMic} title="Hold Space to talk">
          &#127908;
        </button>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Hold Space to talk, or type…" />
      </form>
    </aside>
  )
}
