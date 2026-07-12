import { ArrowUpRight, ArrowDownRight, Gavel, ShieldAlert, FolderOpen } from 'lucide-react'
import { Stamp } from '@/components/ui/stamp'
import { TickMeter } from '@/components/ui/badge'

/** A static, decorative docket sheet shown in the hero. Not interactive. */
export function HeroPreview() {
  const bars = [42, 55, 48, 63, 58, 72, 68, 84, 79, 92, 88, 100]
  const rows = [
    { id: 'CASE-0421', label: 'Ban · raid alt', sev: 'critical', at: '2026-07-12T14:22:00Z' },
    { id: 'CASE-0418', label: 'Mute · spam flood', sev: 'high', at: '2026-07-12T14:09:00Z' },
    { id: 'CASE-0417', label: 'Warn · slur filter', sev: 'medium', at: '2026-07-12T13:51:00Z' },
    { id: 'CASE-0414', label: 'Appeal · approved', sev: 'low', at: '2026-07-12T13:30:00Z' },
  ]
  const kpis = [
    { label: 'Mod actions', value: '1,204', delta: '+8.2%', up: true, icon: Gavel },
    { label: 'Automod blocks', value: '9,417', delta: '+14.6%', up: true, icon: ShieldAlert },
    { label: 'Open cases', value: '23', delta: '-11.0%', up: false, icon: FolderOpen },
  ]
  return (
    <div className="rounded-lg border border-border bg-card shadow-[0_24px_60px_-24px_rgba(20,22,28,0.35)]">
      {/* Window chrome as a records header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full bg-danger/70" />
          <span className="size-2.5 rounded-full bg-warning/70" />
          <span className="size-2.5 rounded-full bg-success/70" />
        </div>
        <span className="font-mono text-[0.6875rem] text-muted-2">app.docket.gg/overview</span>
        <span className="w-10" />
      </div>

      <div className="p-4">
        <div className="grid grid-cols-3 gap-3">
          {kpis.map((k) => (
            <div key={k.label} className="rounded-md border border-border bg-surface p-3">
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-muted">{k.label}</span>
                <k.icon className="size-3.5 text-muted-2" />
              </div>
              <p className="mt-1 font-display text-lg font-semibold text-foreground">{k.value}</p>
              <span
                className={`inline-flex items-center gap-0.5 text-[11px] font-medium ${
                  k.up ? 'text-success' : 'text-danger'
                }`}
              >
                {k.up ? <ArrowUpRight className="size-3" /> : <ArrowDownRight className="size-3" />}
                {k.delta}
              </span>
            </div>
          ))}
        </div>

        <div className="mt-3 rounded-md border border-border bg-surface p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-foreground">Automod activity</span>
            <span className="font-mono text-[0.625rem] uppercase tracking-wider text-muted-2">Last 12h</span>
          </div>
          <div className="mt-4 flex h-24 items-end gap-1.5">
            {bars.map((h, i) => (
              <div
                key={i}
                className="flex-1 rounded-t-[2px] bg-accent"
                style={{ height: `${h}%`, opacity: 0.3 + (i / bars.length) * 0.7 }}
              />
            ))}
          </div>
        </div>

        <div className="mt-3 rounded-md border border-border bg-surface p-3">
          <div className="flex items-center justify-between px-1 pb-2">
            <span className="text-xs font-medium text-foreground">Recent cases</span>
            <span className="font-mono text-[0.625rem] uppercase tracking-wider text-success">Live</span>
          </div>
          <ul className="space-y-1">
            {rows.map((r) => (
              <li
                key={r.id}
                className={`rail rail-${r.sev} flex items-center gap-3 rounded-md bg-card py-1.5 pr-2.5`}
              >
                <TickMeter severity={r.sev} />
                <span className="flex-1 text-[11px] text-foreground">{r.label}</span>
                <Stamp id={r.id} at={r.at} />
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
