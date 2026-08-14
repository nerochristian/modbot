import Link from 'next/link'
import { ArrowRight, LogIn } from 'lucide-react'
import { buttonVariants } from '@/components/ui/button'
import { FieldDesk } from '@/components/marketing/field-desk'
import { CircuitField } from '@/components/marketing/circuit-field'
import { CommandDemo } from '@/components/marketing/command-demo'

/**
 * THE MODERATION FIELD
 *
 * The storefront rebuilt as one dark operating room — because describing
 * moderation is weaker than showing it. The hero IS the desk: an orbital
 * threat gauge and a containment ledger that plays a real raid, attenuates,
 * and goes quiet. Every section below uses its own shape (a type-set line
 * of facts, an open ledger, a right-rail record list). No card grid, no
 * eyebrow/H1/body rhythm — the page doesn't pitch, it runs.
 */

const UNITS = [
  { name: 'Automod', desc: 'Watches every message so a human doesn’t have to be first.' },
  { name: 'Cases', desc: 'Every action lands as a record with a reason, a time and an author.' },
  { name: 'Reports', desc: 'Members flag trouble privately; staff triage without the theatre.' },
  { name: 'Tickets', desc: 'Support stays in private channels with transcripts kept.' },
]

const RECORDS = [
  { who: 'Marcus Lee', role: 'Head moderator · 40k members', quote: 'I stopped waking up to a wall of pings. I wake up to a ledger.' },
  { who: 'Priya N.', role: 'Server owner · 12k members', quote: 'The raid rule paid for itself the first night we turned it on.' },
]

export default function LandingPage() {
  return (
    <>
      {/* ———————————————— THE FIELD — hero as the room ———————————————— */}
      <section className="relative overflow-hidden">
        <CircuitField className="pointer-events-none absolute inset-0 h-full w-full opacity-40" />
        <div className="field-grid-fade grid-texture pointer-events-none absolute inset-0 opacity-45" />
        <div
          className="pointer-events-none absolute right-[8%] top-[-10%] size-[34rem] rounded-full opacity-[0.1] blur-[120px] field-drift"
          style={{ background: 'radial-gradient(circle, var(--brand-from), transparent 70%)' }}
        />

        <div className="relative mx-auto grid max-w-6xl grid-cols-1 items-center gap-14 px-6 pb-20 pt-16 lg:grid-cols-[1.05fr_0.95fr] lg:gap-10 lg:pb-28 lg:pt-24">
          {/* The word — set like an operating statement, not an ad */}
          <div className="max-w-xl">
            <p className="mb-8 font-mono text-[0.6875rem] uppercase tracking-[0.28em] text-muted-2">
              <span className="text-accent">Docket</span> · the moderation field
            </p>
            <h1 className="font-display text-[clamp(3rem,7.5vw,5.25rem)] font-semibold leading-[0.94] tracking-[-0.035em] text-foreground">
              The raid happened.
              <br />
              You read about it
              <br />
              <span className="text-brand-gradient">in the morning.</span>
            </h1>
            <p className="mt-8 max-w-md text-[1.0625rem] leading-relaxed text-muted">
              Docket sits between Discord and your team — absorbing spam, raids and reports,
              and writing every action into one ledger your moderators can actually trust.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-4">
              <Link
                href="/api/auth/discord/authorize"
                className={buttonVariants({ variant: 'primary', size: 'lg', className: 'gap-2.5 px-7' })}
              >
                <LogIn className="size-4" />
                Sign in with Discord
              </Link>
              <Link
                href="#ledger"
                className="focus-ring inline-flex items-center gap-2 font-mono text-xs uppercase tracking-[0.16em] text-muted transition-colors hover:text-foreground"
              >
                Read a morning ledger
                <ArrowRight className="size-3.5" />
              </Link>
            </div>
            <p className="mt-7 font-mono text-[0.625rem] uppercase tracking-[0.16em] text-muted-2">
              Requires live Discord administrator permission
            </p>
          </div>

          {/* The desk */}
          <div>
            <p className="mb-3 flex items-center justify-between font-mono text-[0.625rem] uppercase tracking-[0.16em] text-muted-2">
              <span>Overnight · 02:00–04:00</span>
              <span className="text-threat">Demonstration</span>
            </p>
            <FieldDesk />
          </div>
        </div>
      </section>

      {/* ———— the unit line —— one set line of names, not a card grid ———— */}
      <section className="border-y border-border/60">
        <div className="mx-auto max-w-6xl overflow-x-auto px-6 py-5">
          <div className="flex min-w-max items-baseline gap-8">
            {UNITS.map((u, i) => (
              <div key={u.name} className="group flex items-baseline gap-2.5">
                <span className="font-mono text-[0.5625rem] uppercase tracking-[0.2em] text-muted-2">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span className="font-display text-lg font-semibold text-foreground">{u.name}</span>
                <span className="hidden max-w-52 text-xs leading-snug text-muted transition-opacity group-hover:opacity-100 md:block md:opacity-0">
                  {u.desc}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ————————— THE MORNING LEDGER — an open document in space ————————— */}
      <section id="ledger" className="relative mx-auto max-w-6xl scroll-mt-24 px-6 py-24 lg:py-32">
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-[0.6fr_1.4fr] lg:gap-16">
          <div className="lg:pt-10">
            <p className="mb-6 font-mono text-[0.6875rem] uppercase tracking-[0.28em] text-muted-2">
              <span className="text-accent">What you read</span> at 08:30
            </p>
            <h2 className="font-display text-[clamp(2.25rem,4.5vw,3.4rem)] font-semibold leading-[1.02] tracking-[-0.03em] text-foreground">
              Not a wall of pings.
              <br />
              <span className="text-muted">A page of record.</span>
            </h2>
            <p className="mt-6 max-w-sm text-base leading-relaxed text-muted">
              Every event — blocked, warned, timed out, appealed — arrives with a case ID, a
              timestamp and the rule or moderator that made the call. You don’t reconstruct the night;
              you skim it over coffee and act where it matters.
            </p>
          </div>

          <div className="field-module">
            <span className="field-corner" aria-hidden />
            <div className="border-b border-border/70 px-5 py-3">
              <p className="font-mono text-[0.625rem] uppercase tracking-[0.18em] text-muted">CASES · 2026-07-13 · example</p>
            </div>
            <ul>
              {[
                { id: 'CASE-2850', kind: 'BAN', label: '14-account raid cluster removed', sev: 'text-threat', time: '01:47' },
                { id: 'CASE-2851', kind: 'TIMEOUT', label: 'Caps flood in #general — 10 m', sev: 'text-warning', time: '01:52' },
                { id: 'CASE-2849', kind: 'REPORT', label: '“Possible underage” — pending review', sev: 'text-accent', time: '23:18' },
                { id: 'APPEAL-112', kind: 'APPEAL', label: 'Warn removed after review', sev: 'text-success', time: '21:04' },
              ].map((r, i) => (
                <li
                  key={r.id}
                  className="flex items-center gap-4 px-5 py-3.5 field-rule transition-colors hover:bg-surface-2/50"
                  style={{ animationDelay: `${i * 60}ms` }}
                >
                  <span className="font-mono text-[0.625rem] tabular-nums text-muted-2">{r.time}</span>
                  <span className={`font-mono text-[0.5625rem] font-bold uppercase tracking-[0.14em] ${r.sev}`}>{r.kind}</span>
                  <span className="min-w-0 flex-1 truncate text-sm text-foreground">{r.label}</span>
                  <span className="shrink-0 font-mono text-[0.625rem] uppercase tracking-[0.1em] text-muted-2">{r.id}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* live product beneath the ledger */}
        <div className="mt-20">
          <p className="mb-4 flex items-center justify-between font-mono text-[0.625rem] uppercase tracking-[0.16em] text-muted-2">
            <span>Member record · live demonstration</span>
            <span>Example data</span>
          </p>
          <CommandDemo />
        </div>
      </section>

      {/* ——————— FROM THE DESK — quotes set large, no card chrome ——————— */}
      <section className="border-t border-border/60">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <p className="mb-12 text-center font-mono text-[0.6875rem] uppercase tracking-[0.28em] text-muted-2">
            <span className="text-accent">From the desk</span>
          </p>
          <div className="grid gap-14 md:grid-cols-2">
            {RECORDS.map((r) => (
              <figure key={r.who} className="mx-auto max-w-md text-center">
                <blockquote className="font-display text-[1.45rem] font-medium leading-[1.3] tracking-[-0.015em] text-foreground">
                  “{r.quote}”
                </blockquote>
                <figcaption className="mt-5">
                  <div className="text-sm font-medium text-foreground">{r.who}</div>
                  <div className="mt-0.5 font-mono text-[0.625rem] uppercase tracking-[0.16em] text-muted-2">{r.role}</div>
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>

      {/* ————————— THE RIM — final invitation, wide open ————————— */}
      <section className="relative overflow-hidden border-t border-border/60">
        <div className="pointer-events-none absolute inset-0 grid-texture field-grid-fade opacity-40" />
        <div className="relative mx-auto max-w-3xl px-6 pb-28 pt-24 text-center">
          <p className="mb-8 font-mono text-[0.6875rem] uppercase tracking-[0.28em] text-muted-2">
            <span className="text-success">Rim quiet</span> · your shift starts whenever
          </p>
          <h2 className="font-display text-[clamp(2.5rem,6vw,4.5rem)] font-semibold leading-[0.96] tracking-[-0.035em] text-foreground">
            Put the field
            <br />
            on watch tonight.
          </h2>
          <p className="mx-auto mt-6 max-w-md text-base leading-relaxed text-muted">
            Sign in with Discord. Choose a server you administer. The desk starts writing;
            you start reading in the morning.
          </p>
          <div className="mt-9">
            <Link
              href="/api/auth/discord/authorize"
              className={buttonVariants({ variant: 'primary', size: 'lg', className: 'gap-2.5 px-8' })}
            >
              <LogIn className="size-4" />
              Sign in with Discord
            </Link>
          </div>
          <p className="mt-6 font-mono text-[0.625rem] uppercase tracking-[0.16em] text-muted-2">
            <Link href="/commands" className="transition-colors hover:text-foreground">
              Browse all commands first →
            </Link>
          </p>
        </div>
      </section>
    </>
  )
}
