import { cn } from '@/lib/utils'

type Tone = 'neutral' | 'accent' | 'mint' | 'success' | 'warning' | 'danger' | 'info'

const TONES: Record<Tone, string> = {
  neutral: 'bg-surface-2 text-muted border-border',
  accent: 'bg-accent-soft text-accent border-transparent',
  mint: 'bg-mint-soft text-mint border-transparent',
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
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium',
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

/** Maps a severity to its spine class (the signature left-rail motif). */
export function severitySpine(severity: string): string {
  switch (severity) {
    case 'low':
      return 'spine spine-low'
    case 'medium':
      return 'spine spine-medium'
    case 'high':
      return 'spine spine-high'
    case 'critical':
      return 'spine spine-critical'
    default:
      return 'spine spine-none'
  }
}
