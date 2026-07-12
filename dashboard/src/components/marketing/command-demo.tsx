'use client'

import { useEffect, useRef, useState } from 'react'
import { ShieldCheck, Sparkles } from 'lucide-react'

/**
 * Command demo — the "speak plainly, act precisely" moment. A natural-language
 * moderation command types itself out in a Discord-style composer, then Docket
 * replies with a structured case embed. Cycles through a few examples. This is
 * the reference's typing demo, rebuilt in the blue situation-room language.
 */

type Example = {
  command: string
  channel: string
  reply: {
    title: string
    subject: string
    action: string
    duration: string
    reason: string
    confidence: string
    tags: string[]
  }
}

const EXAMPLES: Example[] = [
  {
    command: '@Docket mute @Vandalizer for 10m for the spam raid',
    channel: '#mod-commands',
    reply: {
      title: 'Case opened · timeout',
      subject: '@Vandalizer',
      action: 'Timeout',
      duration: '10 minutes',
      reason: 'Coordinated spam — 6 messages across 3 channels in 4.2s.',
      confidence: '99.4%',
      tags: ['Auto-filed', 'Raid pattern'],
    },
  },
  {
    command: '/moderate user:@Spammer scope:global reason:advertising',
    channel: '#mod-commands',
    reply: {
      title: 'Case opened · ban',
      subject: '@Spammer',
      action: 'Ban',
      duration: 'Permanent',
      reason: 'Repeat advertising across 4 servers on the network.',
      confidence: '97.1%',
      tags: ['Global scope', 'Network match'],
    },
  },
  {
    command: '@Docket why was @Newcomer flagged?',
    channel: '#mod-commands',
    reply: {
      title: 'Context report',
      subject: '@Newcomer',
      action: 'Watchlist',
      duration: 'Under review',
      reason: 'Account 2h old, posted a known phishing domain once.',
      confidence: '88.0%',
      tags: ['No action yet', 'Low trust'],
    },
  },
]

const TYPE_SPEED = 34
const HOLD_AFTER_TYPE = 2600
const HOLD_AFTER_REPLY = 2400

export function CommandDemo() {
  const [idx, setIdx] = useState(0)
  const [typed, setTyped] = useState('')
  const [showReply, setShowReply] = useState(false)
  const timers = useRef<ReturnType<typeof setTimeout>[]>([])

  useEffect(() => {
    const prefersReduced =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    const ex = EXAMPLES[idx]
    const t = timers.current

    if (prefersReduced) {
      setTyped(ex.command)
      setShowReply(true)
      t.push(setTimeout(() => setIdx((i) => (i + 1) % EXAMPLES.length), 5000))
      return () => t.forEach(clearTimeout)
    }

    setTyped('')
    setShowReply(false)

    // Type the command out character by character.
    for (let c = 1; c <= ex.command.length; c++) {
      t.push(setTimeout(() => setTyped(ex.command.slice(0, c)), c * TYPE_SPEED))
    }
    const typeDone = ex.command.length * TYPE_SPEED
    // Reveal the reply, hold, then advance.
    t.push(setTimeout(() => setShowReply(true), typeDone + HOLD_AFTER_TYPE))
    t.push(
      setTimeout(
        () => setIdx((i) => (i + 1) % EXAMPLES.length),
        typeDone + HOLD_AFTER_TYPE + HOLD_AFTER_REPLY,
      ),
    )

    return () => {
      t.forEach(clearTimeout)
      timers.current = []
    }
  }, [idx])

  const ex = EXAMPLES[idx]

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card">
      {/* Channel header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <span className="font-mono text-[0.6875rem] text-muted-2">{ex.channel}</span>
        <span className="font-mono text-[0.625rem] uppercase tracking-[0.16em] text-accent">Docket · online</span>
      </div>

      <div className="min-h-[300px] space-y-4 p-4">
        {/* Moderator message being typed */}
        <div className="flex items-start gap-3">
          <div className="grid size-8 shrink-0 place-items-center rounded-full bg-surface-2 font-mono text-[0.6875rem] font-semibold text-muted">
            MOD
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-foreground">You</span>
              <span className="font-mono text-[0.625rem] text-muted-2">now</span>
            </div>
            <p className="mt-0.5 font-mono text-[0.8125rem] leading-relaxed text-foreground">
              {renderCommand(typed)}
              {!showReply && <span className="ml-0.5 inline-block h-[1.05em] w-[2px] translate-y-[2px] bg-accent align-middle wire-blip" />}
            </p>
          </div>
        </div>

        {/* Docket structured reply */}
        {showReply && (
          <div className="animate-wire-in flex items-start gap-3">
            <div className="bg-brand-gradient grid size-8 shrink-0 place-items-center rounded-md text-xs font-bold text-white">
              D
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-foreground">Docket</span>
                <span className="rounded-sm bg-accent-soft px-1 font-mono text-[0.5625rem] font-bold uppercase tracking-wide text-accent">
                  Bot
                </span>
                <span className="font-mono text-[0.625rem] text-muted-2">now</span>
              </div>

              {/* The case embed */}
              <div className="mt-2 rounded-md border border-border bg-surface">
                <div className="flex items-center gap-2 border-b border-border px-3 py-2">
                  <ShieldCheck className="size-3.5 text-accent" />
                  <span className="font-mono text-xs font-semibold text-foreground">{ex.reply.title}</span>
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-2.5 p-3">
                  <Cell label="Subject" value={ex.reply.subject} mono />
                  <Cell label="Action" value={ex.reply.action} />
                  <Cell label="Duration" value={ex.reply.duration} />
                  <Cell label="Confidence" value={ex.reply.confidence} accent />
                  <div className="col-span-2">
                    <Cell label="Reason" value={ex.reply.reason} />
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-1.5 border-t border-border px-3 py-2">
                  <Sparkles className="size-3 text-accent" />
                  {ex.reply.tags.map((tag) => (
                    <span key={tag} className="rounded-sm bg-accent-soft px-1.5 py-0.5 font-mono text-[0.5625rem] font-semibold uppercase tracking-wide text-accent">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Composer */}
      <div className="flex items-center gap-2 border-t border-border px-4 py-3">
        <div className="flex-1 rounded-md border border-border bg-surface px-3 py-2 font-mono text-[0.8125rem] text-muted-2">
          Message {ex.channel}
        </div>
        <span className="rounded-md bg-brand-gradient px-3 py-2 text-xs font-semibold text-white">Send</span>
      </div>
    </div>
  )
}

/** Highlight @mentions and /commands inside the typed string. */
function renderCommand(text: string) {
  const parts = text.split(/(@\S+|\/\S+|\bfor\b|\d+m\b)/g)
  return parts.map((p, i) => {
    if (/^@\S+/.test(p)) return <span key={i} className="rounded-sm bg-accent-soft px-0.5 text-accent">{p}</span>
    if (/^\/\S+/.test(p)) return <span key={i} className="text-accent">{p}</span>
    return <span key={i}>{p}</span>
  })
}

function Cell({ label, value, mono, accent }: { label: string; value: string; mono?: boolean; accent?: boolean }) {
  return (
    <div>
      <div className="font-mono text-[0.5625rem] uppercase tracking-[0.14em] text-muted-2">{label}</div>
      <div
        className={
          'mt-0.5 text-xs ' +
          (accent ? 'text-accent font-semibold ' : 'text-foreground ') +
          (mono ? 'font-mono' : '')
        }
      >
        {value}
      </div>
    </div>
  )
}
