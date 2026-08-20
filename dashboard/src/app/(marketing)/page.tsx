import Link from 'next/link'
import { ArrowRight, LogIn, Zap, ShieldCheck, LayoutGrid, SlidersHorizontal, Ban, ShieldAlert } from 'lucide-react'
import { buttonVariants } from '@/components/ui/button'
import { DiscordWindow } from '@/components/marketing/discord-window'
import { CommandDemo } from '@/components/marketing/command-demo'
import { FeatureShowcase } from '@/components/marketing/feature-showcase'
import { StatCard } from '@/components/dashboard/stat-card'

/**
 * Docket's front door — built the way novax.gg proves its own features: a
 * real #mod-log channel as the hero, then a dense run of sections where
 * every claim (automod, cases, protection, tickets…) sits next to a small
 * mockup of that exact product surface instead of an icon and a sentence.
 */

const MODULES = ['Automod', 'Cases', 'Reports', 'Tickets', 'Appeals', 'Risk scoring']

const TRUST = [
  { icon: Zap, title: 'Real-time', desc: 'Automod acts on a message before your mods ever see the ping.' },
  { icon: ShieldCheck, title: 'Secure', desc: 'OAuth only. The dashboard never sees or stores a Discord password.' },
  { icon: LayoutGrid, title: 'Fully featured', desc: 'Automod, cases, reports, tickets, appeals, and risk scoring in one bot.' },
  { icon: SlidersHorizontal, title: 'Configurable', desc: 'Every rule, filter, and permission is tuned per server, not global.' },
]

const ANALYTICS = [
  {
    label: 'Joins (7d)',
    value: '312',
    delta: 6.4,
    spark: Array.from({ length: 12 }, (_, i) => ({ label: String(i), value: 18 + Math.round(Math.sin(i / 1.6) * 8 + i * 0.6) })),
    color: 'var(--success)',
  },
  {
    label: 'Automod blocks (7d)',
    value: '9,417',
    delta: 14.6,
    spark: Array.from({ length: 12 }, (_, i) => ({ label: String(i), value: 40 + Math.round(Math.cos(i / 1.4) * 14 + i * 3) })),
    color: 'var(--threat)',
  },
  {
    label: 'Messages (7d)',
    value: '184k',
    delta: 3.1,
    spark: Array.from({ length: 12 }, (_, i) => ({ label: String(i), value: 60 + Math.round(Math.sin(i / 1.2) * 10 + i * 1.4) })),
    color: 'var(--accent)',
  },
  {
    label: 'Voice minutes (7d)',
    value: '22.8k',
    delta: 9.8,
    spark: Array.from({ length: 12 }, (_, i) => ({ label: String(i), value: 25 + Math.round(Math.cos(i / 1.8) * 9 + i * 1.1) })),
    color: 'var(--brand-cyan)',
  },
]

export default function LandingPage() {
  return (
    <>
      {/* ————————————————————— HERO ————————————————————— */}
      <section className="relative overflow-hidden">
        <div className="soft-grid pointer-events-none absolute inset-0 opacity-60" />

        <div className="relative mx-auto grid max-w-6xl grid-cols-1 items-center gap-14 px-6 pb-20 pt-14 lg:grid-cols-[1.05fr_0.95fr] lg:gap-10 lg:pb-28 lg:pt-20">
          <div className="max-w-xl">
            <p className="mb-6 inline-flex items-center gap-2 rounded-full border border-accent-line bg-accent-soft px-3 py-1 font-mono text-[0.6875rem] uppercase tracking-[0.16em] text-accent">
              <span className="size-1.5 rounded-full bg-accent wire-blip" />
              Built for Discord moderation
            </p>
            <h1 className="font-display text-[clamp(2.75rem,6.5vw,4.5rem)] font-semibold leading-[1.02] tracking-[-0.03em] text-foreground">
              Moderation that doesn’t
              <br />
              wait for <span className="text-brand-gradient">a human</span>
              <br />
              to be online.
            </h1>
            <p className="mt-7 max-w-md text-[1.0625rem] leading-relaxed text-muted">
              Docket sits in your server watching for spam, raids, and rule-breakers — then hands
              your mod team a clean case file instead of a wall of pings to sort through.
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
                href="/commands"
                className="focus-ring inline-flex items-center gap-2 rounded-md px-1 py-2 text-sm font-medium text-muted transition-colors hover:text-foreground"
              >
                Browse all commands
                <ArrowRight className="size-3.5" />
              </Link>
            </div>
            <p className="mt-7 font-mono text-[0.625rem] uppercase tracking-[0.16em] text-muted-2">
              Requires live Discord administrator permission
            </p>

            {/* module strip — what's actually in the box */}
            <div className="mt-10 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-border pt-6">
              {MODULES.map((m) => (
                <span key={m} className="font-mono text-[0.6875rem] uppercase tracking-[0.12em] text-muted-2">
                  {m}
                </span>
              ))}
            </div>
          </div>

          <div className="relative">
            <DiscordWindow />

            {/* floating proof chips — the room has other things happening too */}
            <div
              aria-hidden
              className="wire-float glass-panel absolute -left-6 top-6 hidden items-center gap-2 rounded-full px-3.5 py-2 text-xs font-medium text-foreground shadow-lg sm:flex"
            >
              <Ban className="size-3.5 text-threat" />
              14 accounts banned
            </div>
            <div
              aria-hidden
              className="wire-float-slow glass-panel absolute -bottom-5 right-2 hidden items-center gap-2 rounded-full px-3.5 py-2 text-xs font-medium text-foreground shadow-lg sm:flex"
            >
              <ShieldAlert className="size-3.5 text-success" />
              Anti-raid active
            </div>
          </div>
        </div>
      </section>

      {/* ————————————————————— TRUST STRIP ————————————————————— */}
      <section className="border-t border-border">
        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-8 px-6 py-14 sm:grid-cols-2 lg:grid-cols-4">
          {TRUST.map((t) => (
            <div key={t.title} className="flex items-start gap-3">
              <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-accent-soft text-accent">
                <t.icon className="size-4.5" />
              </span>
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-foreground">{t.title}</h3>
                <p className="mt-1 text-[0.8125rem] leading-snug text-muted">{t.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ————————————————————— FEATURE SHOWCASE ————————————————————— */}
      <section id="features" className="scroll-mt-24 border-t border-border">
        <div className="mx-auto max-w-6xl px-6 py-20 lg:py-28">
          <div className="max-w-lg">
            <p className="mb-4 font-mono text-[0.6875rem] uppercase tracking-[0.28em] text-accent">What Docket does</p>
            <h2 className="font-display text-[clamp(2rem,4vw,2.75rem)] font-semibold leading-[1.05] tracking-[-0.025em] text-foreground">
              Every claim, proven on the spot.
            </h2>
          </div>
          <div className="mt-14">
            <FeatureShowcase />
          </div>
        </div>
      </section>

      {/* ————————————————————— LIVE DEMO ————————————————————— */}
      <section className="border-t border-border">
        <div className="mx-auto max-w-4xl px-6 py-20 lg:py-28">
          <p className="mb-4 text-center font-mono text-[0.6875rem] uppercase tracking-[0.28em] text-accent">
            Try it yourself
          </p>
          <h2 className="text-center font-display text-[clamp(2rem,4vw,2.75rem)] font-semibold leading-[1.05] tracking-[-0.025em] text-foreground">
            Ping a member, get their record.
          </h2>
          <p className="mx-auto mt-4 max-w-md text-center text-base leading-relaxed text-muted">
            This is the same lookup your moderators use in Discord — click a member below.
          </p>
          <div className="mt-10">
            <CommandDemo />
          </div>
        </div>
      </section>

      {/* ————————————————————— ANALYTICS ————————————————————— */}
      <section className="border-t border-border">
        <div className="mx-auto max-w-6xl px-6 py-20 lg:py-28">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="max-w-lg">
              <p className="mb-4 font-mono text-[0.6875rem] uppercase tracking-[0.28em] text-accent">Server insight</p>
              <h2 className="font-display text-[clamp(2rem,4vw,2.75rem)] font-semibold leading-[1.05] tracking-[-0.025em] text-foreground">
                Know your server, not just your case log.
              </h2>
            </div>
            <p className="font-mono text-[0.625rem] uppercase tracking-[0.16em] text-muted-2">Example data</p>
          </div>
          <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {ANALYTICS.map((a) => (
              <StatCard key={a.label} label={a.label} value={a.value} delta={a.delta} spark={a.spark} />
            ))}
          </div>
        </div>
      </section>

      {/* ————————————————————— HOW IT WORKS ————————————————————— */}
      <section id="setup" className="scroll-mt-24 border-t border-border">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
            {[
              { n: '01', title: 'Add Docket', desc: 'Sign in with Discord and add the bot to a server you administer.' },
              { n: '02', title: 'Set your rules', desc: 'Turn on the filters you want and pick a case-log channel.' },
              { n: '03', title: 'Read the log', desc: 'Every action lands in your dashboard with a reason attached.' },
            ].map((s) => (
              <div key={s.n} className="flex items-start gap-3">
                <span className="grid size-8 shrink-0 place-items-center rounded-full border border-accent-line font-mono text-[0.6875rem] font-bold text-accent">
                  {s.n}
                </span>
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-foreground">{s.title}</h3>
                  <p className="mt-1 text-[0.8125rem] leading-snug text-muted">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ————————————————————— FINAL CTA ————————————————————— */}
      <section className="relative overflow-hidden border-t border-border">
        <div className="soft-grid pointer-events-none absolute inset-0 opacity-50" />
        <div
          aria-hidden
          className="blue-orb pointer-events-none absolute left-1/2 top-0 size-[40rem] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-70"
        />
        <div className="relative mx-auto max-w-3xl px-6 pb-28 pt-24 text-center">
          <h2 className="font-display text-[clamp(2.25rem,5.5vw,3.75rem)] font-semibold leading-[1.02] tracking-[-0.03em] text-foreground">
            Add Docket to your server.
          </h2>
          <p className="mx-auto mt-5 max-w-md text-base leading-relaxed text-muted">
            Sign in with Discord, pick a server you administer, and Docket starts watching
            immediately.
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
