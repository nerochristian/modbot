'use client'

import { useEffect, useRef, useState } from 'react'

/**
 * The Field Desk — the marketing hero. Not an illustration of moderation;
 * a working slice of the room. A raid streams in, the orbital gauge rises,
 * and the containment ledger writes itself until the rim goes quiet.
 *
 * Reduced-motion renders the settled end-state instantly.
 */

type Line = {
  id: number
  user: string
  reason: string
}

const RAID: Line[] = [
  { id: 1, user: 'user4821', reason: 'scam link' },
  { id: 2, user: 'user9033', reason: 'scam link' },
  { id: 3, user: 'g1ftdrop', reason: 'phishing' },
  { id: 4, user: 'user1102', reason: 'mention flood' },
  { id: 5, user: 'nitr0_bot', reason: 'scam link' },
  { id: 6, user: 'user7740', reason: 'invite spam' },
  { id: 7, user: 'freegift88', reason: 'phishing' },
]

const TOTAL = 214
const ROW_MS = 460
const ARC_SEGMENTS = 40
const ARC_SWEEP = 260 // degrees of arc drawn, from -210 to +50

function polar(cx: number, cy: number, r: number, deg: number) {
  const rad = ((deg - 90) * Math.PI) / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}
function arcPath(cx: number, cy: number, r: number, from: number, to: number) {
  const s = polar(cx, cy, r, from)
  const e = polar(cx, cy, r, to)
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${to - from > 180 ? 1 : 0} 1 ${e.x} ${e.y}`
}

export function FieldDesk() {
  const [level, setLevel] = useState(0) // 0..1
  const [lines, setLines] = useState<Line[]>([])
  const [quelled, setQuelled] = useState(false)
  const started = useRef(false)

  useEffect(() => {
    const reduced =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (started.current) return
    started.current = true
    const timers: ReturnType<typeof setTimeout>[] = []

    if (reduced) {
      timers.push(
        setTimeout(() => {
          setLevel(0.08)
          setLines(RAID.slice(-3))
          setQuelled(true)
        }, 0),
      )
      return () => timers.forEach(clearTimeout)
    }

    // Gauge swells to a peak as the raid streams in, then drains to quiet.
    const peakAt = 500 + RAID.length * ROW_MS
    const steps = 40
    for (let i = 1; i <= steps; i++) {
      timers.push(setTimeout(() => setLevel((i / steps) * 0.92), 300 + ((peakAt - 300) * i) / steps))
    }
    for (let i = 1; i <= steps; i++) {
      timers.push(
        setTimeout(
          () => setLevel(0.92 * (1 - i / steps) + 0.08),
          peakAt + 500 + (1400 * i) / steps,
        ),
      )
    }

    RAID.forEach((line, i) => {
      timers.push(setTimeout(() => setLines((l) => [...l, line].slice(-4)), 500 + i * ROW_MS))
    })
    timers.push(setTimeout(() => setQuelled(true), peakAt + 1600))
    return () => timers.forEach(clearTimeout)
  }, [])

  const deg = -130 + ARC_SWEEP * level
  const active = Math.round(level * ARC_SEGMENTS)
  const contained = Math.round(level * TOTAL)

  return (
    <div className="relative select-none">
      {/* ambient glow behind the desk */}
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-1/2 -z-10 size-[36rem] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-[0.14] blur-[100px] field-drift"
        style={{ background: 'radial-gradient(circle, var(--accent) 0%, var(--brand-cyan) 45%, transparent 70%)' }}
      />

      <div className="field-module mx-auto w-full max-w-[26rem]">
        <span className="field-corner" aria-hidden />
        {/* header — the channel being watched */}
        <div className="flex items-center justify-between border-b border-border/70 px-4 py-2.5">
          <div className="flex items-center gap-2">
            <span className={`inline-flex size-1.5 rounded-full ${quelled ? 'bg-success' : 'bg-threat'} wire-blip`} />
            <span className="font-mono text-[0.625rem] uppercase tracking-[0.16em] text-muted">the-nexus / #general</span>
          </div>
          <span className="font-mono text-[0.5625rem] uppercase tracking-[0.18em] text-muted-2">
            {quelled ? 'quiet · contained' : 'live · absorbing'}
          </span>
        </div>

        <div className="grid grid-cols-[auto_1fr] items-center gap-5 px-5 py-5">
          {/* the orbital gauge — threat as measured arc, not a HUD */}
          <div className="relative">
            <svg width="168" height="168" viewBox="0 0 168 168" className="-rotate-0">
              <defs>
                <linearGradient id="fieldArc" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="var(--threat)" />
                  <stop offset="60%" stopColor="var(--accent)" />
                  <stop offset="100%" stopColor="var(--brand-cyan)" />
                </linearGradient>
              </defs>
              {/* tick ring */}
              {Array.from({ length: ARC_SEGMENTS }).map((_, i) => {
                const d = -130 + (ARC_SWEEP / (ARC_SEGMENTS - 1)) * i
                const p1 = polar(84, 84, 76, d)
                const p2 = polar(84, 84, 70, d)
                const on = i < active
                return (
                  <line
                    key={i}
                    x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
                    stroke={on ? 'var(--accent)' : 'color-mix(in srgb, var(--foreground) 14%, transparent)'}
                    strokeWidth={i % 5 === 0 ? 1.6 : 1}
                    className="field-gauge-tick"
                    style={{ transition: `stroke 120ms ease ${i * 10}ms` }}
                  />
                )
              })}
              {/* base arc */}
              <path
                d={arcPath(84, 84, 62, -130, 130)}
                fill="none"
                stroke="color-mix(in srgb, var(--foreground) 8%, transparent)"
                strokeWidth="5"
                strokeLinecap="round"
              />
              {/* live arc */}
              <path
                d={arcPath(84, 84, 62, -130, Math.max(-129, deg))}
                fill="none"
                stroke="url(#fieldArc)"
                strokeWidth="5"
                strokeLinecap="round"
                className="field-gauge-arc"
                style={{ transition: 'all 90ms linear' }}
              />
              {/* needle tip */}
              <circle
                cx={polar(84, 84, 62, Math.max(-129, deg)).x}
                cy={polar(84, 84, 62, Math.max(-129, deg)).y}
                r="2.6"
                fill={quelled ? 'var(--brand-cyan)' : 'var(--threat)'}
                style={{ transition: 'cx 90ms linear, cy 90ms linear' }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span
                className="font-mono text-[1.9rem] font-semibold leading-none tabular-nums"
                style={{ color: quelled ? 'var(--success)' : 'var(--foreground)' }}
              >
                {contained}
              </span>
              <span className="mt-1 font-mono text-[0.5625rem] uppercase tracking-[0.18em] text-muted-2">
                {quelled ? 'contained' : 'events held'}
              </span>
            </div>
          </div>

          {/* containment ledger — the raid, as paperwork */}
          <div className="min-w-0">
            <p className="mb-2 flex items-center justify-between font-mono text-[0.5625rem] uppercase tracking-[0.18em] text-muted-2">
              <span>Containment log</span>
              <span>UTC</span>
            </p>
            <ul className="space-y-1.5">
              {lines.length === 0 && (
                <li className="font-mono text-[0.6875rem] text-muted-2">— standing by —</li>
              )}
              {lines.map((l) => (
                <li key={l.id} className="field-ledger-row field-rule flex items-baseline gap-2 pb-1">
                  <span className="truncate font-mono text-[0.6875rem] text-muted">{l.user}</span>
                  <span className="ml-auto shrink-0 font-mono text-[0.5625rem] uppercase tracking-[0.12em] text-threat">blocked</span>
                  <span className="w-16 shrink-0 text-right font-mono text-[0.5625rem] uppercase tracking-[0.08em] text-muted-2">{l.reason}</span>
                </li>
              ))}
            </ul>
            {quelled && (
              <p className="mt-3 border-t border-border/70 pt-2 font-mono text-[0.5625rem] uppercase tracking-[0.18em] text-success">
                Rim quiet · nobody was online
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
