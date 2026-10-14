import { useEffect, useRef } from 'react'
import { AGENTS, agentStyle, toFeed } from '../agents'
import type { AgentEvent } from '../types'

interface Props {
  events: AgentEvent[]
  running: boolean
  error: string | null
}

export function ActivityFeed({ events, running, error }: Props) {
  const lines = toFeed(events)
  const endRef = useRef<HTMLDivElement>(null)
  const involved = new Set(events.map((e) => e.agent))
  const lastAgent = events.length ? events[events.length - 1].agent : null

  useEffect(() => {
    if (running) endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [lines.length, running])

  return (
    <section className="feed-panel" aria-label="Agent activity">
      <div className="feed-head">
        <h3 className="panel-title">Agent activity</h3>
        <div className="crew">
          {AGENTS.map((a) => {
            const active = running && lastAgent === a.name
            const on = involved.has(a.name)
            return (
              <span
                key={a.name}
                className={`crew-chip ${on ? 'on' : ''} ${active ? 'active' : ''}`}
                style={{ '--agent': a.color, '--tint': a.tint } as React.CSSProperties}
                title={`${a.name}: ${a.role}`}
              >
                <span aria-hidden>{a.icon}</span> {a.short}
              </span>
            )
          })}
        </div>
      </div>

      {error && <div className="callout err"><p>Couldn't refresh activity: {error}</p></div>}

      <ol className="feed">
        {lines.length === 0 && !running && (
          <li className="feed-empty">
            No run on this ticket yet. Start the agent team and you'll see each agent's steps and tool calls here.
          </li>
        )}
        {lines.map((line) => {
          const a = agentStyle(line.event.agent)
          const target = line.event.delegated_to ? agentStyle(line.event.delegated_to) : null
          return (
            <li
              key={line.key}
              className={`feed-line ev-${line.event.event} ${line.event.depth > 0 ? 'nested' : ''}`}
              style={{ '--agent': a.color, '--tint': a.tint, '--depth': line.event.depth } as React.CSSProperties}
            >
              <span className="avatar" aria-hidden>{a.icon}</span>
              <div className="feed-body">
                <div className="feed-meta">
                  <strong className="agent-name">{line.event.agent}</strong>
                  <span className="verb">
                    {target ? (
                      <>
                        {line.verb.replace(line.event.delegated_to ?? '', '')}
                        <span className="handoff" style={{ '--agent': target.color, '--tint': target.tint } as React.CSSProperties}>
                          {target.icon} {target.name}
                        </span>
                      </>
                    ) : (
                      line.verb
                    )}
                  </span>
                  <span className="t">+{line.seconds}s</span>
                </div>
                {line.text && <p className="said">{line.text}</p>}
                {line.tools.length > 0 && (
                  <div className="tools">
                    {line.tools.map((tool) => (
                      <code key={tool} className="tool">{tool}</code>
                    ))}
                  </div>
                )}
              </div>
            </li>
          )
        })}
        {running && (
          <li className="feed-line typing" style={{ '--agent': agentStyle(lastAgent ?? 'Boss').color } as React.CSSProperties}>
            <span className="avatar" aria-hidden>{agentStyle(lastAgent ?? 'Boss').icon}</span>
            <div className="feed-body">
              <span className="dots"><i /><i /><i /></span>
              <span className="muted"> {lines.length === 0 ? 'Boss is reading the ticket…' : `${lastAgent} is working…`}</span>
            </div>
          </li>
        )}
      </ol>
      <div ref={endRef} />
    </section>
  )
}
