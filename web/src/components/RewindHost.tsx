import { useEffect, useRef, useState } from 'react'

// A minimal MCP Apps host: renders ChronoGrid's ui://chronogrid/rewind.html view in a sandboxed
// iframe and speaks the ext-apps postMessage protocol (initialize -> tool-input -> tool-result).

interface Props {
  data: any
  onClose: () => void
}

export function RewindHost({ data, onClose }: Props) {
  const frame = useRef<HTMLIFrameElement>(null)
  const ready = useRef(false)
  const [height, setHeight] = useState(560)
  const latest = useRef(data)
  latest.current = data

  const send = (msg: object) => frame.current?.contentWindow?.postMessage({ jsonrpc: '2.0', ...msg }, '*')
  const pushResult = () => {
    const d = latest.current
    send({ method: 'ui/notifications/tool-input', params: { arguments: { object: d?.object } } })
    send({
      method: 'ui/notifications/tool-result',
      params: { content: [{ type: 'text', text: d?.say ?? '' }], structuredContent: d },
    })
  }

  useEffect(() => {
    const onMessage = (ev: MessageEvent) => {
      if (ev.source !== frame.current?.contentWindow) return
      const msg = ev.data
      if (!msg || msg.jsonrpc !== '2.0') return
      if (msg.method === 'ui/initialize' && msg.id !== undefined) {
        send({
          id: msg.id,
          result: {
            protocolVersion: msg.params?.protocolVersion ?? '2026-01-26',
            hostInfo: { name: 'chronogrid-ambient-screen', version: '0.1.0' },
            hostCapabilities: {},
            hostContext: { theme: 'dark', displayMode: 'inline', platform: 'web' },
          },
        })
      } else if (msg.method === 'ui/notifications/initialized') {
        ready.current = true
        pushResult()
        frame.current?.focus()
      } else if (msg.method === 'ui/notifications/size-changed') {
        setHeight(Math.min(900, Math.max(320, msg.params?.height ?? 560)))
      } else if (msg.method === 'ui/notifications/request-teardown') {
        onClose()
      }
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [onClose])

  useEffect(() => {
    if (ready.current) {
      pushResult()
      frame.current?.focus()
    }
  }, [data])

  return (
    <div className="panel rewind">
      <div className="panel-title">
        <span>Rewind</span>
        <small>MCP App &middot; ui://chronogrid/rewind.html &middot; &larr; &rarr; history &middot; Back to close</small>
      </div>
      <iframe
        ref={frame}
        title="ChronoGrid rewind"
        src="/apps/rewind.html"
        sandbox="allow-scripts"
        style={{ height }}
      />
    </div>
  )
}
