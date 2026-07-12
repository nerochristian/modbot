'use client'

import { useEffect, useRef, useState } from 'react'

/**
 * The Live Wire — the landing page's signature moment. On load, a raid of
 * spoofed accounts streams into a channel feed and Docket's automod stamps
 * each one BLOCKED in real time; a counter climbs to 300 and the board
 * settles into the payoff. Motion IS the product demonstration.
 *
 * Respects reduced-motion: the settled end-state renders immediately (all
 * rows present, counter at final, no streaming) via CSS overrides + the
 * prefersReduced short-circuit below.
 */

type Row = {
  id: number
  user: string
  content: string
  verdict: 'blocked' | 'flagged'
  reason: string
}

const RAID: Row[] = [
  { id: 1, user: 'user4821', content: '@everyone free nitro → grabnitro.gg', verdict: 'blocked', reason: 'scam link' },
  { id: 2, user: 'user9033', content: 'free nitro here!! discocl.aim/gift', verdict: 'blocked', reason: 'scam link' },
  { id: 3, user: 'g1ftdrop', content: 'CLAIM NOW steamcommunlty.ru', verdict: 'blocked', reason: 'phishing' },
  { id: 4, user: 'user1102', content: '@everyone @everyone @everyone', verdict: 'blocked', reason: 'mention flood' },
  { id: 5, user: 'nitr0_bot', content: 'free nitro → grabnitro.gg', verdict: 'blocked', reason: 'scam link' },
  { id: 6, user: 'user7740', content: 'join disc0rd.gift/xyz for free', verdict: 'blocked', reason: 'invite spam' },
  { id: 7, user: 'freegift88', content: 'steamcommunlty.ru/claim', verdict: 'blocked', reason: 'phishing' },
  { id: 8, user: 'user2251', content: 'FREE NITRO FREE NITRO FREE', verdict: 'flagged', reason: 'caps + repeat' },
]

const FINAL_COUNT = 300
const ROW_INTERVAL = 420

export function LiveWire() {
  const [visible, setVisible] = useState<Row[]>([])
  const [count, setCount] = useState(0)
  const [settled, setSettled] = useState(false)
  const startedRef = useRef(false)

  useEffect(() => {
    const prefersReduced =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (startedRef.current) return
    startedRef.current = true

    const timers: ReturnType<typeof setTimeout>[] = []

    if (prefersReduced) {
      // Settle to the end-state on the next tick (avoids sync setState in effect).
      timers.push(
        setTimeout(() => {
          setVisible(RAID)
          setCount(FINAL_COUNT)
          setSettled(true)
        }, 0),
      )
      return () => timers.forEach(clearTimeout)
    }

    // Stream the rows in.
    RAID.forEach((row, i) => {
      timers.push(
        setTimeout(() => {
          setVisible((v) => [...v, row])
        }, 500 + i * ROW_INTERVAL),
      )
    })

    // Climb the counter from 0 → 300 across the stream, then settle.
    const climbStart = 700
    const climbDuration = RAID.length * ROW_INTERVAL
    const climbSteps = 60
    for (let s = 1; s <= climbSteps; s++) {
      timers.push(
        setTimeout(() => {
          setCount(Math.round((FINAL_COUNT * s) / climbSteps))
        }, climbStart + (climbDuration * s) / climbSteps),
      )
    }

    timers.push(
      setTimeout(() => setSettled(true), 500 + RAID.length * ROW_INTERVAL + 400),
    )

    return () => timers.forEach(clearTimeout)
  }, [])

  return (
    <div className="relative">
      {/* Floating glass status widgets — adapted from the reference hero. */}
      <div className="absolute -left-5 -top-5 z-20 hidden items-center gap-2.5 rounded-lg border border-border bg-surface/90 px-3.5 py-2.5 shadow-xl backdrop-blur wire-float sm:flex">
        <span className="inline-flex size-2.5 rounded-full bg-success wire-blip" />
        <div className="text-left">
          <span className="block font-mono text-[0.5625rem] font-semibold uppercase tracking-[0.14em] text-muted-2">Shield status</span>
          <span className="text-xs font-semibold text-foreground">Raid protection · active</span>
        </div>
      </div>
      <div className="absolute -bottom-6 -right-4 z-20 hidden items-center gap-3 rounded-lg border border-border bg-surface/90 px-3.5 py-2.5 shadow-xl backdrop-blur wire-float-slow sm:flex">
        <span className="bg-brand-gradient grid size-8 place-items-center rounded-md text-white">
          <Zap className="size-4" />
        </span>
        <div className="text-left">
          <span className="block font-mono text-[0.5625rem] font-semibold uppercase tracking-[0.14em] text-muted-2">Decision engine</span>
          <span className="text-xs font-semibold text-foreground">142,429 cases resolved</span>
        </div>
      </div>

      <div className="wire-sweep ring-brand relative overflow-hidden rounded-lg border border-border bg-card">
        {/* Board header — channel + live status */}
        <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
          <div className="flex items-center gap-2">
            <span className="wire-blip inline-flex size-2 rounded-full bg-threat" />
            <span className="font-mono text-[0.6875rem] uppercase tracking-[0.14em] text-muted">
              The Nexus / #general
            </span>
        </div>
        <span className="font-mono text-[0.625rem] uppercase tracking-[0.16em] text-accent">
          Automod · live
        </span>
      </div>

      {/* The feed — older rows dissolve into a mask at the top, like a live console. */}
      <div
        className="scanfield relative h-[300px] overflow-hidden px-3 py-3"
        style={{
          maskImage: 'linear-gradient(to bottom, transparent 0, #000 56px)',
          WebkitMaskImage: 'linear-gradient(to bottom, transparent 0, #000 56px)',
        }}
      >
        <ul className="flex flex-col justify-end gap-1.5">
          {visible.map((row) => (
            <li
              key={row.id}
              className="animate-wire-in animate-wire-flash flex items-center gap-3 rounded-md px-2.5 py-2"
            >
              <span className="font-mono text-[0.6875rem] text-muted-2">{row.user}</span>
              <span className="min-w-0 flex-1 truncate text-[0.8125rem] text-muted line-through decoration-threat/50">
                {row.content}
              </span>
              <span
                className={
                  'animate-wire-stamp shrink-0 rounded-sm border px-1.5 py-0.5 font-mono text-[0.5625rem] font-bold uppercase tracking-[0.1em] ' +
                  (row.verdict === 'blocked'
                    ? 'border-threat/40 bg-threat-soft text-threat'
                    : 'border-warning/40 bg-warning-soft text-warning')
                }
              >
                {row.verdict}
              </span>
            </li>
          ))}
        </ul>
      </div>

        {/* The payoff bar */}
        <div className="flex items-center justify-between border-t border-border px-4 py-3">
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-2xl font-semibold tabular-nums text-threat">
              {count}
            </span>
            <span className="text-xs text-muted">accounts stopped</span>
          </div>
          <div
            className={
              'flex items-center gap-2 font-mono text-[0.6875rem] uppercase tracking-[0.12em] transition-opacity duration-500 ' +
              (settled ? 'text-accent opacity-100' : 'opacity-0')
            }
          >
            <span className="inline-flex size-1.5 rounded-full bg-accent" />
            Contained · 180ms
          </div>
        </div>
      </div>
    </div>
  )
}
