import Link from 'next/link'
import { Logo } from '@/components/logo'
import { PublicThemeToggle } from '@/components/marketing/theme-toggle'
import { Stamp } from '@/components/ui/stamp'
import { TickMeter } from '@/components/ui/badge'

const DOCKET_SAMPLE = [
  { id: 'CASE-2847', label: 'Ban · raid alt cluster', sev: 'critical', at: '2026-07-12T14:22:00Z' },
  { id: 'CASE-2846', label: 'Mute · mention flood', sev: 'high', at: '2026-07-12T14:03:00Z' },
  { id: 'CASE-2844', label: 'Warn · invite link', sev: 'medium', at: '2026-07-12T13:41:00Z' },
  { id: 'CASE-2841', label: 'Appeal · approved', sev: 'low', at: '2026-07-12T13:12:00Z' },
]

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-full lg:grid-cols-[1fr_1.05fr]">
      <div className="flex flex-col px-4 py-6 sm:px-8">
        <div className="flex items-center justify-between">
          <Link href="/" className="focus-ring rounded-md">
            <Logo />
          </Link>
          <PublicThemeToggle />
        </div>
        <div className="flex flex-1 items-center justify-center py-10">
          <div className="w-full max-w-sm">{children}</div>
        </div>
        <p className="text-center font-mono text-xs text-muted-2">© 2026 Docket · Demo environment</p>
      </div>

      {/* Side panel — a live docket sheet, not a gradient. */}
      <div className="relative hidden flex-col justify-between overflow-hidden border-l border-border bg-surface p-12 lg:flex">
        <div className="grid-texture pointer-events-none absolute inset-0 opacity-50" />

        <div className="relative">
          <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">
            Today’s docket
          </p>
          <blockquote className="mt-5 max-w-md font-display text-2xl font-semibold leading-snug tracking-tight text-foreground">
            The overwhelmed shift becomes a calm one. Automod files the noise; every case and appeal
            lives on one desk.
          </blockquote>
          <p className="mt-4 text-sm text-muted">Marcus Lee · Head Moderator, The Nexus</p>
        </div>

        <div className="relative rounded-lg border border-border bg-card p-3 shadow-[0_24px_60px_-30px_rgba(20,22,28,0.4)]">
          <div className="flex items-center justify-between px-1 pb-2">
            <span className="text-xs font-medium text-foreground">Open cases</span>
            <span className="font-mono text-[0.625rem] uppercase tracking-wider text-success">Live</span>
          </div>
          <ul className="space-y-1">
            {DOCKET_SAMPLE.map((r) => (
              <li
                key={r.id}
                className={`rail rail-${r.sev} flex items-center gap-3 rounded-md bg-surface py-1.5 pr-2.5`}
              >
                <TickMeter severity={r.sev} />
                <span className="flex-1 text-[11px] text-foreground">{r.label}</span>
                <Stamp id={r.id} at={r.at} />
              </li>
            ))}
          </ul>
        </div>

        <div className="relative flex gap-8">
          <div>
            <p className="font-display text-2xl font-semibold text-foreground">2.5M+</p>
            <p className="text-sm text-muted">Messages scanned daily</p>
          </div>
          <div>
            <p className="font-display text-2xl font-semibold text-foreground">40k+</p>
            <p className="text-sm text-muted">Communities protected</p>
          </div>
        </div>
      </div>
    </div>
  )
}
