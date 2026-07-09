import { ArrowUpRight, Gavel, ShieldAlert, FolderOpen } from 'lucide-react'

/** A static, decorative moderation deck mock shown in the hero. Not interactive. */
export function HeroPreview() {
  const bars = [42, 55, 48, 63, 58, 72, 68, 84, 79, 92, 88, 100]
  const actions = [
    { id: '#CASE-0421', label: 'Ban · raid alt', spine: 'spine-critical' },
    { id: '#CASE-0418', label: 'Mute · spam flood', spine: 'spine-high' },
    { id: '#CASE-0417', label: 'Warn · slur filter', spine: 'spine-medium' },
    { id: '#CASE-0414', label: 'Appeal · approved', spine: 'spine-mint' },
  ]
  return (
    <div className="rounded-2xl border border-border bg-card p-4 shadow-2xl shadow-black/10">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full bg-danger/70" />
          <span className="size-2.5 rounded-full bg-warning/70" />
          <span className="size-2.5 rounded-full bg-success/70" />
        </div>
        <span className="text-xs text-muted-2">app.aegis.gg/deck</span>
        <span className="w-10" />
      </div>

      <div className="grid grid-cols-3 gap-3 pt-4">
        {[
          { label: 'Mod actions', value: '1,204', delta: '+8.2%', icon: Gavel },
          { label: 'Automod blocks', value: '9,417', delta: '+14.6%', icon: ShieldAlert },
          { label: 'Open cases', value: '23', delta: '-11.0%', icon: FolderOpen },
        ].map((k) => (
          <div key={k.label} className="rounded-xl border border-border bg-surface p-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-muted">{k.label}</span>
              <k.icon className="size-3.5 text-muted-2" />
            </div>
            <p className="mt-1 text-lg font-semibold text-foreground">{k.value}</p>
            <span className="inline-flex items-center gap-0.5 text-[11px] font-medium text-mint">
              <ArrowUpRight className="size-3" />
              {k.delta}
            </span>
          </div>
        ))}
      </div>

      <div className="mt-3 rounded-xl border border-border bg-surface p-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-foreground">Automod activity</span>
          <span className="text-[11px] text-muted-2">Last 12 hours</span>
        </div>
        <div className="mt-4 flex h-24 items-end gap-1.5">
          {bars.map((h, i) => (
            <div
              key={i}
              className="flex-1 rounded-t bg-accent/80"
              style={{ height: `${h}%`, opacity: 0.35 + (i / bars.length) * 0.65 }}
            />
          ))}
        </div>
      </div>

      <div className="mt-3 rounded-xl border border-border bg-surface p-3">
        <div className="flex items-center justify-between px-1 pb-2">
          <span className="text-xs font-medium text-foreground">Recent actions</span>
          <span className="text-[11px] text-muted-2">Live</span>
        </div>
        <ul className="space-y-1.5">
          {actions.map((a) => (
            <li
              key={a.id}
              className={`spine ${a.spine} flex items-center justify-between rounded-md bg-card py-1.5 pl-3 pr-2.5`}
            >
              <span className="text-[11px] text-foreground">{a.label}</span>
              <span className="mono-id text-[11px] text-muted-2">{a.id}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
