import { cn } from '@/lib/utils'

type Tone = 'neutral' | 'accent' | 'mint' | 'success' | 'warning' | 'danger' | 'info'

const TONES: Record<Tone, string> = {
  neutral: 'bg-surface-2 text-muted border-border',
  accent: 'bg-accent-soft text-accent border-accent-line',
  mint: 'bg-success-soft text-success border-transparent',
  success: 'bg-success-soft text-success border-transparent',
  warning: 'bg-warning-soft text-warning border-transparent',
  danger: 'bg-danger-soft text-danger border-transparent',
  info: 'bg-info-soft text-info border-transparent',
}

export function Badge({
  tone = 'neutral',
  dot = false,
  className,
  children,
}: {
  tone?: Tone
  dot?: boolean
  className?: string
  children: React.ReactNode
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-xs font-medium',
        TONES[tone],
        className,
      )}
    >
      {dot && <span className="size-1.5 rounded-full bg-current" />}
      {children}
    </span>
  )
}

/** Maps common status strings to a semantic tone. */
export function statusTone(status: string): Tone {
  switch (status) {
    // healthy / positive
    case 'active':
    case 'good':
    case 'paid':
    case 'ready':
    case 'success':
    case 'resolved':
    case 'approved':
    case 'operational':
      return 'success'
    // informational / in-progress
    case 'trialing':
    case 'invited':
    case 'open':
    case 'pending':
    case 'generating':
    case 'scheduled':
      return 'info'
    // caution
    case 'past_due':
    case 'watchlist':
    case 'muted':
    case 'appealed':
    case 'expired':
    case 'warning':
    case 'degraded':
      return 'warning'
    // negative / severe
    case 'churned':
    case 'banned':
    case 'suspended':
    case 'denied':
    case 'failed':
    case 'down':
    case 'void':
      return 'danger'
    default:
      return 'neutral'
  }
}

export type Severity = 'low' | 'medium' | 'high' | 'critical'

/** Maps an infraction/rule severity to a badge tone. */
export function severityTone(severity: string): Tone {
  switch (severity) {
    case 'low':
      return 'info'
    case 'medium':
      return 'warning'
    case 'high':
      return 'danger'
    case 'critical':
      return 'danger'
    default:
      return 'neutral'
  }
}

const SEVERITY_ORDER = ['none', 'low', 'medium', 'high', 'critical'] as const

/** Maps a severity to the docket-rail modifier (the thin left gutter marker). */
export function severityRail(severity: string): string {
  const level = (SEVERITY_ORDER as readonly string[]).includes(severity) ? severity : 'none'
  return `rail rail-${level}`
}

/** Back-compat alias — older call sites still import severitySpine. */
export const severitySpine = severityRail

/** Severity as a filled level 1–5 for the tick-meter signature. */
export function severityLevel(severity: string): number {
  switch (severity) {
    case 'low':
      return 2
    case 'medium':
      return 3
    case 'high':
      return 4
    case 'critical':
      return 5
    default:
      return 1
  }
}

/**
 * Tick-meter — the signature severity gauge. Renders a 5-tick bar filled to
 * the severity level and colored only toward the vermilion (critical) end.
 */
export function TickMeter({
  severity,
  className,
}: {
  severity: string
  className?: string
}) {
  const level = severityLevel(severity)
  const color = `var(--sev-${(SEVERITY_ORDER as readonly string[]).includes(severity) ? severity : 'none'})`
  return (
    <span
      className={cn('tickmeter', className)}
      role="img"
      aria-label={`Severity: ${severity || 'none'} (${level} of 5)`}
      style={{ ['--tick-color' as string]: color }}
    >
      {[0, 1, 2, 3, 4].map((i) => (
        <span key={i} className={cn('tick', i < level && 'on')} />
      ))}
    </span>
  )
}
