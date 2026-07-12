'use client'

import { useEffect, useRef, useState } from 'react'
import { ShieldCheck, Gavel, Clock, Ban, AlertTriangle, Eye, CornerDownLeft } from 'lucide-react'
import { TickMeter } from '@/components/ui/badge'

/**
 * Command demo — interactive. Ping a member and Docket pulls up their real
 * action history: standing, risk, and a timeline of every moderation action on
 * record. Click a member chip (or the composer types one out on first load) to
 * run the lookup. Backed by a local roster so it works with no live backend.
 */

type ActionKind = 'ban' | 'mute' | 'warn' | 'watch' | 'note' | 'unmute'

type Action = {
  kind: ActionKind
  label: string
  detail: string
  when: string
  by: string
}

type Member = {
  id: string
  handle: string
  initials: string
  color: string
  standing: 'good' | 'watchlist' | 'muted' | 'banned'
  standingLabel: string
  risk: 'none' | 'low' | 'medium' | 'high' | 'critical'
  joined: string
  summary: string
  actions: Action[]
}

const MEMBERS: Member[] = [
  {
    id: '1',
    handle: '@Vandalizer',
    initials: 'VZ',
    color: '#ff4d4d',
    standing: 'banned',
    standingLabel: 'Banned',
    risk: 'critical',
    joined: '2h before ban',
    summary: 'Raid account. Escalated from mute to permanent ban within one session.',
    actions: [
      { kind: 'ban', label: 'Permanent ban', detail: 'Coordinated raid — 6 msgs / 3 channels in 4.2s', when: '07·12 14:22Z', by: 'raid-shield' },
      { kind: 'mute', label: 'Timeout · 10m', detail: 'Mention flood — @everyone ×3', when: '07·12 14:19Z', by: '@you' },
      { kind: 'warn', label: 'Warned', detail: 'Posted scam link (grabnitro.gg)', when: '07·12 14:18Z', by: 'automod' },
    ],
  },
  {
    id: '2',
    handle: '@vibe_master',
    initials: 'VM',
    color: '#e0942e',
    standing: 'watchlist',
    standingLabel: 'Watchlist',
    risk: 'medium',
    joined: '4 months ago',
    summary: 'Long-time member with a recent pattern of heated arguments. No bans.',
    actions: [
      { kind: 'watch', label: 'Added to watchlist', detail: 'Third heated report in 7 days', when: '07·10 21:04Z', by: '@Priya' },
      { kind: 'warn', label: 'Warned', detail: 'Targeted insults in #general', when: '07·08 18:40Z', by: '@Marcus' },
      { kind: 'mute', label: 'Timeout · 1h', detail: 'Spoiler dumping after warning', when: '06·29 11:12Z', by: '@you' },
      { kind: 'note', label: 'Mod note', detail: '“Calms down when DMed directly.”', when: '06·29 11:15Z', by: '@Marcus' },
    ],
  },
  {
    id: '3',
    handle: '@Newcomer',
    initials: 'NC',
    color: '#1e78ff',
    standing: 'watchlist',
    standingLabel: 'Under review',
    risk: 'low',
    joined: '2 hours ago',
    summary: 'New account flagged once. No action taken yet — low confidence.',
    actions: [
      { kind: 'watch', label: 'Flagged for review', detail: 'Account 2h old posted a known phishing domain once', when: '07·12 13:58Z', by: 'automod' },
      { kind: 'note', label: 'Mod note', detail: '“Could be a compromised link, not intent. Watching.”', when: '07·12 14:01Z', by: '@you' },
    ],
  },
  {
    id: '4',
    handle: '@RegularRuby',
    initials: 'RR',
    color: '#33d6ff',
    standing: 'good',
    standingLabel: 'Good standing',
    risk: 'none',
    joined: '1 year ago',
    summary: 'Trusted regular. One old, resolved case. Clean since.',
    actions: [
      { kind: 'unmute', label: 'Timeout lifted', detail: 'Appeal approved — false positive on caps filter', when: '01·14 09:30Z', by: '@Marcus' },
      { kind: 'mute', label: 'Timeout · 10m', detail: 'Caps filter (later overturned)', when: '01·14 09:02Z', by: 'automod' },
    ],
  },
]

const ICON: Record<ActionKind, typeof Ban> = {
  ban: Ban,
  mute: Clock,
  warn: AlertTriangle,
  watch: Eye,
  note: Gavel,
  unmute: ShieldCheck,
}

const ACTION_TONE: Record<ActionKind, string> = {
  ban: 'text-threat',
  mute: 'text-warning',
  warn: 'text-warning',
  watch: 'text-accent',
  note: 'text-muted',
  unmute: 'text-success',
}

const STANDING_TONE: Record<Member['standing'], string> = {
  good: 'bg-success-soft text-success',
  watchlist: 'bg-warning-soft text-warning',
  muted: 'bg-warning-soft text-warning',
  banned: 'bg-threat-soft text-threat',
}

const TYPE_SPEED = 30

export function CommandDemo() {
  const [selected, setSelected] = useState<Member | null>(null)
  const [typed, setTyped] = useState('')
  const [typing, setTyping] = useState(false)
  const startedRef = useRef(false)
  const timers = useRef<ReturnType<typeof setTimeout>[]>([])

  function clearTimers() {
    timers.current.forEach(clearTimeout)
    timers.current = []
  }

  /** Run the lookup for a member: type the command, then reveal the record. */
  function lookup(member: Member, opts?: { instant?: boolean }) {
    clearTimers()
    const command = `@Docket show actions for ${member.handle}`
    const prefersReduced =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (opts?.instant || prefersReduced) {
      setTyped(command)
      setTyping(false)
      setSelected(member)
      return
    }

    setSelected(null)
    setTyping(true)
    setTyped('')
    for (let c = 1; c <= command.length; c++) {
      timers.current.push(setTimeout(() => setTyped(command.slice(0, c)), c * TYPE_SPEED))
    }
    timers.current.push(
      setTimeout(() => {
        setTyping(false)
        setSelected(member)
      }, command.length * TYPE_SPEED + 380),
    )
  }

  // Auto-run the first example once on mount so the section demonstrates itself.
  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true
    timers.current.push(setTimeout(() => lookup(MEMBERS[0]), 400))
    return clearTimers
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card">
      {/* Channel header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <span className="font-mono text-[0.6875rem] text-muted-2">#mod-commands</span>
        <span className="font-mono text-[0.625rem] uppercase tracking-[0.16em] text-accent">Docket · online</span>
      </div>

      <div className="min-h-[360px] space-y-4 p-4">
        {/* Moderator message */}
        <div className="flex items-start gap-3">
          <div className="grid size-8 shrink-0 place-items-center rounded-full bg-surface-2 font-mono text-[0.6875rem] font-semibold text-muted">
            MOD
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-foreground">You</span>
              <span className="font-mono text-[0.625rem] text-muted-2">now</span>
            </div>
            <p className="mt-0.5 min-h-[1.25rem] font-mono text-[0.8125rem] leading-relaxed text-foreground">
              {renderCommand(typed)}
              {typing && (
                <span className="ml-0.5 inline-block h-[1.05em] w-[2px] translate-y-[2px] bg-accent align-middle wire-blip" />
              )}
            </p>
          </div>
        </div>

        {/* Docket reply — the member's record */}
        {selected && (
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

              {/* Member dossier */}
              <div className="mt-2 rounded-md border border-border bg-surface">
                {/* Identity row */}
                <div className="flex items-center gap-3 border-b border-border p-3">
                  <span
                    className="grid size-9 shrink-0 place-items-center rounded-md font-mono text-xs font-bold text-white"
                    style={{ backgroundColor: selected.color }}
                  >
                    {selected.initials}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-sm font-semibold text-foreground">{selected.handle}</span>
                      <span className={`rounded-sm px-1.5 py-0.5 font-mono text-[0.5625rem] font-bold uppercase tracking-wide ${STANDING_TONE[selected.standing]}`}>
                        {selected.standingLabel}
                      </span>
                    </div>
                    <p className="mt-0.5 text-[0.6875rem] text-muted">Joined {selected.joined}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <TickMeter severity={selected.risk} />
                    <span className="font-mono text-[0.5625rem] uppercase tracking-wide text-muted-2">Risk: {selected.risk}</span>
                  </div>
                </div>

                {/* Summary */}
                <p className="border-b border-border px-3 py-2 text-xs leading-relaxed text-muted">{selected.summary}</p>

                {/* Action history timeline */}
                <div className="p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="font-mono text-[0.5625rem] uppercase tracking-[0.14em] text-muted-2">Action history</span>
                    <span className="font-mono text-[0.5625rem] text-muted-2">{selected.actions.length} on record</span>
                  </div>
                  <ul className="space-y-2">
                    {selected.actions.map((a, i) => {
                      const Icon = ICON[a.kind]
                      return (
                        <li key={i} className="flex items-start gap-2.5">
                          <span className={`mt-0.5 shrink-0 ${ACTION_TONE[a.kind]}`}>
                            <Icon className="size-3.5" />
                          </span>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-baseline justify-between gap-2">
                              <span className="text-xs font-semibold text-foreground">{a.label}</span>
                              <span className="shrink-0 font-mono text-[0.5625rem] text-muted-2">{a.when}</span>
                            </div>
                            <p className="text-[0.6875rem] leading-snug text-muted">{a.detail}</p>
                            <span className="font-mono text-[0.5625rem] text-muted-2">by {a.by}</span>
                          </div>
                        </li>
                      )
                    })}
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Interactive ping bar — click a member to pull their record */}
      <div className="border-t border-border px-4 py-3">
        <div className="mb-2 flex items-center gap-1.5 font-mono text-[0.5625rem] uppercase tracking-[0.14em] text-muted-2">
          <CornerDownLeft className="size-3" />
          Ping a member to see their actions
        </div>
        <div className="flex flex-wrap gap-1.5">
          {MEMBERS.map((m) => {
            const active = selected?.id === m.id
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => lookup(m)}
                className={
                  'focus-ring rounded-md border px-2.5 py-1.5 font-mono text-xs transition-colors ' +
                  (active
                    ? 'border-accent-line bg-accent-soft text-accent'
                    : 'border-border bg-surface text-muted hover:border-accent-line hover:text-foreground')
                }
              >
                {m.handle}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}

/** Highlight @mentions inside the typed command string. */
function renderCommand(text: string) {
  const parts = text.split(/(@\S+)/g)
  return parts.map((p, i) =>
    /^@\S+/.test(p) ? (
      <span key={i} className="rounded-sm bg-accent-soft px-0.5 text-accent">
        {p}
      </span>
    ) : (
      <span key={i}>{p}</span>
    ),
  )
}
