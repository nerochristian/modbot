'use client'

import { useEffect, useRef, useState } from 'react'
import { Ban, Clock, ShieldCheck, Hash, Users } from 'lucide-react'

/**
 * The hero visual: a real Discord channel, not an illustration of one.
 * #mod-log fills with Docket's own ban/timeout embeds during a raid, then
 * settles on a "contained" summary — the same embed chrome (avatar, BOT tag,
 * colored left bar) Discord renders for real. Reduced-motion shows the
 * settled end-state immediately.
 */

type Tone = 'ban' | 'timeout' | 'contained'

type Entry = {
  id: number
  tone: Tone
  title: string
  detail: string
  time: string
}

const RAID: Entry[] = [
  { id: 1, tone: 'ban', title: 'Banned @user4821', detail: 'Raid pattern — 6 messages across 3 channels in 4s', time: '02:14' },
  { id: 2, tone: 'ban', title: 'Banned @g1ftdrop', detail: 'Known phishing domain posted in #general', time: '02:14' },
  { id: 3, tone: 'timeout', title: 'Timed out @user1102 · 10m', detail: 'Mention flood — @everyone ×3', time: '02:15' },
  { id: 4, tone: 'ban', title: 'Banned @nitr0_bot', detail: 'Nitro gift-link scam', time: '02:15' },
]

const CONTAINED: Entry = {
  id: 99,
  tone: 'contained',
  title: 'Raid contained',
  detail: '14 accounts removed in 38 seconds. Zero messages reached #general.',
  time: '02:15',
}

const TONE_META: Record<Tone, { icon: typeof Ban; bar: string; iconColor: string }> = {
  ban: { icon: Ban, bar: 'var(--threat)', iconColor: 'text-threat' },
  timeout: { icon: Clock, bar: 'var(--warning)', iconColor: 'text-warning' },
  contained: { icon: ShieldCheck, bar: 'var(--success)', iconColor: 'text-success' },
}

const ROW_MS = 650

export function DiscordWindow() {
  const [entries, setEntries] = useState<Entry[]>([])
  const [live, setLive] = useState(true)
  const started = useRef(false)

  useEffect(() => {
    if (started.current) return
    started.current = true
    const reduced =
      typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const timers: ReturnType<typeof setTimeout>[] = []

    if (reduced) {
      setEntries([...RAID.slice(-2), CONTAINED])
      setLive(false)
      return
    }

    RAID.forEach((entry, i) => {
      timers.push(setTimeout(() => setEntries((e) => [...e, entry]), 500 + i * ROW_MS))
    })
    timers.push(
      setTimeout(() => {
        setEntries((e) => [...e, CONTAINED])
        setLive(false)
      }, 500 + RAID.length * ROW_MS + 300),
    )
    return () => timers.forEach(clearTimeout)
  }, [])

  return (
    <div className="relative select-none">
      <div
        aria-hidden
        className="blue-orb pointer-events-none absolute left-1/2 top-1/2 -z-10 size-[34rem] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-90"
      />

      <div className="glass-panel mx-auto w-full max-w-[27rem] overflow-hidden rounded-2xl">
        {/* channel header */}
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex min-w-0 items-center gap-2">
            <Hash className="size-4 shrink-0 text-muted-2" />
            <span className="truncate text-sm font-semibold text-foreground">mod-log</span>
            <span className="hidden truncate text-xs text-muted-2 sm:inline">— the-nexus</span>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <span className="hidden items-center gap-1 font-mono text-[0.625rem] text-muted-2 sm:flex">
              <Users className="size-3" />
              12,404
            </span>
            <span className="flex items-center gap-1.5 font-mono text-[0.625rem] uppercase tracking-[0.1em]">
              <span className={`size-1.5 rounded-full ${live ? 'bg-threat' : 'bg-success'} wire-blip`} />
              <span className={live ? 'text-threat' : 'text-success'}>{live ? 'live' : 'contained'}</span>
            </span>
          </div>
        </div>

        {/* message list */}
        <div className="min-h-[21rem] space-y-3.5 px-4 py-4">
          {entries.length === 0 && (
            <p className="pt-8 text-center font-mono text-xs text-muted-2">watching #mod-log…</p>
          )}
          {entries.map((entry) => {
            const meta = TONE_META[entry.tone]
            const Icon = meta.icon
            return (
              <div key={entry.id} className="animate-wire-in flex items-start gap-3">
                <span className="bg-brand-gradient grid size-8 shrink-0 place-items-center rounded-lg text-xs font-bold text-white">
                  D
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-foreground">Docket</span>
                    <span className="rounded-sm bg-accent-soft px-1 py-px font-mono text-[0.5625rem] font-bold uppercase tracking-wide text-accent">
                      Bot
                    </span>
                    <span className="font-mono text-[0.625rem] text-muted-2">{entry.time}</span>
                  </div>
                  <div
                    className="mt-1.5 rounded-md border border-border bg-surface-2/70 py-2 pl-3 pr-3"
                    style={{ borderLeft: `3px solid ${meta.bar}` }}
                  >
                    <p className={`flex items-center gap-1.5 text-[0.8125rem] font-medium text-foreground`}>
                      <Icon className={`size-3.5 shrink-0 ${meta.iconColor}`} />
                      {entry.title}
                    </p>
                    <p className="mt-0.5 text-xs leading-snug text-muted">{entry.detail}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        <div className="border-t border-border px-4 py-2.5">
          <p className="font-mono text-[0.5625rem] uppercase tracking-[0.14em] text-muted-2">
            Demonstration · example server
          </p>
        </div>
      </div>
    </div>
  )
}
