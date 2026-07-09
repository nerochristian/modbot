import { cn } from '@/lib/utils'

type Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info'

const TONES: Record<Tone, string> = {
  neutral: 'bg-surface-2 text-muted border-border',
  accent: 'bg-accent-soft text-accent border-transparent',
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
    case 'active':
    case 'paid':
    case 'ready':
    case 'success':
      return 'success'
    case 'trialing':
    case 'invited':
    case 'open':
    case 'generating':
    case 'scheduled':
      return 'info'
    case 'past_due':
    case 'warning':
      return 'warning'
    case 'churned':
    case 'suspended':
    case 'failed':
    case 'void':
      return 'danger'
    default:
      return 'neutral'
  }
}
