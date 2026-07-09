import { ArrowUpRight, Users, DollarSign, Activity } from 'lucide-react'

/** A static, decorative dashboard mock shown in the hero. Not interactive. */
export function HeroPreview() {
  const bars = [42, 55, 48, 63, 58, 72, 68, 84, 79, 92, 88, 100]
  return (
    <div className="rounded-2xl border border-border bg-card p-4 shadow-2xl shadow-black/10">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full bg-danger/70" />
          <span className="size-2.5 rounded-full bg-warning/70" />
          <span className="size-2.5 rounded-full bg-success/70" />
        </div>
        <span className="text-xs text-muted-2">app.nebula.dev/dashboard</span>
        <span className="w-10" />
      </div>

      <div className="grid grid-cols-3 gap-3 pt-4">
        {[
          { label: 'Revenue', value: '$128.4k', delta: '+12.4%', icon: DollarSign },
          { label: 'Active users', value: '8,912', delta: '+4.1%', icon: Users },
          { label: 'Conversion', value: '3.8%', delta: '+0.6%', icon: Activity },
        ].map((k) => (
          <div key={k.label} className="rounded-xl border border-border bg-surface p-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-muted">{k.label}</span>
              <k.icon className="size-3.5 text-muted-2" />
            </div>
            <p className="mt-1 text-lg font-semibold text-foreground">{k.value}</p>
            <span className="inline-flex items-center gap-0.5 text-[11px] font-medium text-success">
              <ArrowUpRight className="size-3" />
              {k.delta}
            </span>
          </div>
        ))}
      </div>

      <div className="mt-3 rounded-xl border border-border bg-surface p-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-foreground">Revenue over time</span>
          <span className="text-[11px] text-muted-2">Last 12 months</span>
        </div>
        <div className="mt-4 flex h-28 items-end gap-1.5">
          {bars.map((h, i) => (
            <div
              key={i}
              className="flex-1 rounded-t bg-accent/80"
              style={{ height: `${h}%`, opacity: 0.35 + (i / bars.length) * 0.65 }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
