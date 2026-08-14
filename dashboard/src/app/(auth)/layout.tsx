import Link from 'next/link'
import { Logo } from '@/components/logo'
import { PublicThemeToggle } from '@/components/marketing/theme-toggle'
import { Stamp } from '@/components/ui/stamp'
import { TickMeter } from '@/components/ui/badge'

/**
 * Sign-in — "the handover desk." The left pane asks for the badge; the right
 * pane is the ledger that accumulated since the operator was away: a
 * chronological feed of real-shaped cases and system events, stamped and
 * severity-metered like any other docket surface in the product.
 */

const LEDGER = [
  { id: 'CASE-2851', label: 'Timeout · 10 m — caps flood in #general', sev: 'medium', at: '2026-07-13T01:52:00Z', by: 'automod' },
  { id: 'CASE-2850', label: 'Ban · raid alt cluster (14 accounts)', sev: 'critical', at: '2026-07-13T01:47:00Z', by: 'automod' },
  { id: 'CASE-2849', label: 'Report filed · “possible underage user”', sev: 'high', at: '2026-07-12T23:18:00Z', by: 'member · anonymous' },
  { id: 'APPEAL-112', label: 'Appeal approved · warn removed', sev: 'low', at: '2026-07-12T21:04:00Z', by: '@vera' },
  { id: 'CASE-2847', label: 'Kick · slur in voice-chat title', sev: 'high', at: '2026-07-12T19:36:00Z', by: '@marcus' },
  { id: 'NOTE-338', label: 'Staff note added to member 4419', sev: 'none', at: '2026-07-12T16:02:00Z', by: '@jonah' },
]

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-full lg:grid-cols-[1.08fr_1fr]">
      {/* Ledger pane — what happened while you were away (desktop first so
          screen readers hit the log before the form; on mobile it collapses
          to a compact strip under the form). */}
      <div className="relative hidden flex-col justify-between overflow-hidden border-r border-border bg-surface p-12 lg:flex">
        <div className="grid-texture pointer-events-none absolute inset-0 opacity-50" />
        <div className="scanfield pointer-events-none absolute inset-0 opacity-25" />
        <div
          className="pointer-events-none absolute -left-24 bottom-0 h-[360px] w-[360px] rounded-full opacity-15 blur-[110px]"
          style={{ background: 'radial-gradient(circle, var(--brand-from, #005bf3), transparent 70%)' }}
        />

        {/* Header — the desk label */}
        <div className="relative">
          <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">
            Since your last shift
          </p>
          <h2 className="mt-3 max-w-sm font-display text-[2rem] font-semibold leading-[1.08] tracking-[-0.02em] text-foreground">
            The desk kept working.
            <span className="text-muted"> Here’s the paper trail.</span>
          </h2>
        </div>

        {/* The ledger — a chronological docket */}
        <div className="relative my-10">
          <div className="mb-3 flex items-center justify-between font-mono text-[0.625rem] uppercase tracking-[0.14em] text-muted-2">
            <span>Server log · The Nexus</span>
            <span>UTC · example data</span>
          </div>
          <ul className="divide-y divide-border rounded-lg border border-border bg-card shadow-[0_24px_60px_-30px_rgba(20,22,28,0.4)]">
            {LEDGER.map((row) => (
              <li
                key={row.id}
                className={`docket-ledger-row rail rail-${row.sev} flex items-center gap-3 px-3.5 py-2.5`}
              >
                <TickMeter severity={row.sev} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[0.8125rem] font-medium text-foreground">{row.label}</p>
                  <p className="mt-0.5 font-mono text-[0.625rem] uppercase tracking-[0.1em] text-muted-2">
                    by {row.by}
                  </p>
                </div>
                <Stamp id={row.id} at={row.at} className="shrink-0" />
              </li>
            ))}
          </ul>
          <p className="mt-3 text-right font-mono text-[0.625rem] uppercase tracking-[0.14em] text-muted-2">
            + 41 more entries, all stamped &amp; searchable
          </p>
        </div>

        {/* Closing facts */}
        <div className="relative flex gap-10 border-t border-border pt-6">
          <div>
            <p className="font-display text-lg font-semibold leading-tight text-foreground">
              Guild-scoped
            </p>
            <p className="mt-1 text-sm text-muted">Every workspace stays isolated</p>
          </div>
          <div>
            <p className="font-display text-lg font-semibold leading-tight text-foreground">
              Auditable
            </p>
            <p className="mt-1 text-sm text-muted">Nothing happens without a record</p>
          </div>
          <div>
            <p className="font-display text-lg font-semibold leading-tight text-foreground">
              OAuth-only
            </p>
            <p className="mt-1 text-sm text-muted">No passwords on this desk</p>
          </div>
        </div>
      </div>

      {/* Form pane — the badge reader */}
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
        <p className="text-center font-mono text-xs text-muted-2">
          © 2026 Docket · Discord-secured access
        </p>
      </div>
    </div>
  )
}
