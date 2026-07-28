'use client'

import { BadgeCheck } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Live mock of the bot's Pillow-rendered welcome card. Mirrors the renderer's
 * layout math (1000×420 canvas, accent frame, glow, ring, pill, badges) so the
 * designer is honestly representative; final render ships via /testwelcome.
 */
export function WelcomeCardPreview({ values }: { values: Record<string, unknown> }) {
  const str = (key: string, fallback = '') => {
    const value = values[key]
    return typeof value === 'string' && value.trim() ? value.trim() : fallback
  }
  const num = (key: string, fallback: number) => {
    const parsed = Number(values[key])
    return Number.isFinite(parsed) && String(values[key]).trim() !== '' ? parsed : fallback
  }
  const bool = (key: string, fallback: boolean) => (values[key] === undefined ? fallback : values[key] === true)
  const color = (key: string, fallback: string) => {
    const value = str(key)
    return /^#?[0-9a-fA-F]{6}$/.test(value) ? (value.startsWith('#') ? value : `#${value}`) : fallback
  }

  const accent = color('welcome_card_accent', '#5865f2')
  const ringColor = color('welcome_card_ring_color', accent)
  const textColor = color('welcome_card_text_color', '#ffffff')
  const bgUrl = str('welcome_bg_url')
  const blur = Math.max(0, Math.min(40, num('welcome_card_blur', 12)))
  const dim = Math.max(0, Math.min(90, num('welcome_card_overlay', 55))) / 100
  const left = str('welcome_card_layout', 'center') === 'left'
  const label = (str('welcome_card_label', 'WELCOME') || 'WELCOME').toUpperCase()
  const subtitle = str('welcome_card_subtitle', 'to {server}').replace('{server}', 'your server').replace('{count}', '1,337')
  const showRing = bool('welcome_card_ring', true)
  const showBadges = bool('welcome_card_badges', true)
  const showCount = bool('welcome_card_member_count', true)

  const meta = ['@newmember', ...(showCount ? ['Member #1,337'] : [])].join('  ·  ')

  return (
    <div>
      <p className="mb-2 font-mono text-[0.625rem] font-bold uppercase tracking-[0.18em] text-accent">Live preview</p>
      <div className="relative aspect-[1000/420] w-full overflow-hidden rounded-[1.75rem] border border-border bg-[#0b0e17] shadow-lg">
        {/* Background */}
        {bgUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={bgUrl}
            alt=""
            className="absolute inset-0 h-full w-full object-cover"
            style={{ filter: blur > 0 ? `blur(${Math.round(blur * 0.6)}px)` : undefined, transform: blur > 0 ? 'scale(1.08)' : undefined }}
          />
        ) : (
          <div
            className="absolute inset-0"
            style={{ background: `radial-gradient(120% 140% at 20% 0%, ${accent}55 0%, #0b0e17 60%)`, filter: blur > 0 ? `blur(${Math.round(blur * 0.6)}px)` : undefined, transform: blur > 0 ? 'scale(1.08)' : undefined }}
          />
        )}
        {/* Dim + vignette */}
        <div className="absolute inset-0 bg-[#04060c]" style={{ opacity: dim }} />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
        {/* Accent frame */}
        <div className="pointer-events-none absolute inset-[9px] rounded-[1.3rem] border-2" style={{ borderColor: `${accent}70` }} />

        <div className={cn('absolute inset-0 flex p-[7%]', left ? 'items-center gap-[6%]' : 'flex-col items-center justify-start text-center')}>
          {/* Avatar */}
          <div className={cn('relative shrink-0', left ? 'size-[31%]' : 'mt-[2%] size-[36%]')} style={{ maxWidth: 168, maxHeight: 168, aspectRatio: '1' }}>
            <div className="absolute -inset-[18%] rounded-full opacity-70 blur-2xl" style={{ background: accent }} />
            <div
              className="relative grid size-full place-items-center rounded-full bg-gradient-to-br from-slate-500 to-slate-700 font-display text-3xl font-bold text-white"
              style={showRing ? { boxShadow: `0 0 0 6px ${ringColor}` } : undefined}
            >
              N
            </div>
          </div>

          {/* Text block */}
          <div className={cn('min-w-0', left ? 'flex flex-col items-start' : 'mt-[3.5%] flex flex-col items-center')}>
            <span
              className="rounded-full px-3 py-1 text-[0.6rem] font-bold tracking-[0.14em]"
              style={{ background: `${accent}2e`, color: accent }}
            >
              {label}
            </span>
            <p className="mt-2 truncate font-display text-2xl font-bold leading-tight sm:text-3xl" style={{ color: textColor }}>
              New Member
            </p>
            {subtitle && <p className="mt-1 text-xs sm:text-sm" style={{ color: `${textColor}b8` }}>{subtitle}</p>}
            <p className="mt-0.5 text-xs font-medium sm:text-sm" style={{ color: accent }}>{meta}</p>
            {showBadges && (
              <div className="mt-2.5 flex items-center gap-1.5">
                {[0, 1, 2].map((index) => (
                  <span key={index} className="grid size-6 place-items-center rounded-md bg-white/10">
                    <BadgeCheck className="size-3.5" style={{ color: accent }} />
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
      <p className="mt-2 text-xs text-muted-2">Approximate mock. Render the real card in Discord with /testwelcome.</p>
    </div>
  )
}
