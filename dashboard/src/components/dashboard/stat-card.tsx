import { ArrowDownRight, ArrowUpRight, type LucideIcon } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Sparkline } from '@/components/charts'
import { cn } from '@/lib/utils'

export function StatCard({
  label,
  value,
  delta,
  icon: Icon,
  spark,
  invertDelta = false,
}: {
  label: string
  value: string
  delta?: number
  icon?: LucideIcon
  spark?: { label: string; value: number }[]
  invertDelta?: boolean
}) {
  const positive = delta !== undefined && delta >= 0
  // For metrics like bans, a lower value is good — invert the color meaning.
  const good = invertDelta ? !positive : positive

  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <p className="font-mono text-[0.6875rem] font-medium uppercase tracking-[0.1em] text-muted">{label}</p>
          <p className="mt-2 font-display text-[1.75rem] font-semibold leading-none tracking-tight text-foreground">{value}</p>
        </div>
        {Icon && (
          <span className="flex size-9 items-center justify-center rounded-md bg-accent-soft text-accent">
            <Icon className="size-4.5" />
          </span>
        )}
      </div>
      <div className="mt-3 flex items-center justify-between gap-3">
        {delta !== undefined && (
          <span
            className={cn(
              'inline-flex items-center gap-0.5 text-sm font-medium',
              good ? 'text-success' : 'text-danger',
            )}
          >
            {positive ? <ArrowUpRight className="size-4" /> : <ArrowDownRight className="size-4" />}
            {Math.abs(delta).toFixed(1)}%
          </span>
        )}
        {spark && (
          <div className="h-9 w-24">
            <Sparkline data={spark} height={36} color={good ? 'var(--success)' : 'var(--accent)'} />
          </div>
        )}
      </div>
    </Card>
  )
}
