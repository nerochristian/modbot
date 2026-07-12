import Link from 'next/link'
import {
  ShieldAlert,
  Gavel,
  Scale,
  Users2,
  SlidersHorizontal,
  Activity,
  ArrowRight,
  LogIn,
} from 'lucide-react'
import { buttonVariants } from '@/components/ui/button'
import { HeroPreview } from '@/components/marketing/hero-preview'
import { Pricing } from '@/components/marketing/pricing'
import { Faq } from '@/components/marketing/faq'

const FEATURES = [
  {
    tag: 'AUTOMOD',
    icon: ShieldAlert,
    title: 'Rules that act before you wake up',
    desc: 'Layer rules for spam, slurs, invite links, mention floods, and raid patterns. Each one scores content in real time and files the case itself — so the log is already clean when your shift starts.',
  },
  {
    tag: 'CASES',
    icon: Gavel,
    title: 'Every action becomes a record',
    desc: 'Warns, mutes, kicks, and bans open a case with full history, evidence, and moderator notes. Nothing gets lost in the handoff between shifts.',
  },
  {
    tag: 'APPEALS',
    icon: Scale,
    title: 'Decisions stay consistent',
    desc: 'Members appeal through a structured queue your team reviews, votes on, and resolves. Every ruling is attributable and on the record.',
  },
  {
    tag: 'MEMBERS',
    icon: Users2,
    title: 'Read the whole history at a glance',
    desc: 'A complete file on every member — join date, prior infractions, risk signals, watchlist status — with server-side search, filters, and sorting.',
  },
  {
    tag: 'ROLES',
    icon: SlidersHorizontal,
    title: 'Access maps to how your team works',
    desc: 'Admin, Moderator, and Helper roles with an editable permission matrix. Enforced in the console and on every API route — not just hidden in the UI.',
  },
  {
    tag: 'CONSOLE',
    icon: Activity,
    title: 'Configure the desk to your shift',
    desc: 'Reorder widgets, hide what you don’t need, set severity thresholds, themes, and density. Every preference is saved to your account.',
  },
]

const STATS = [
  { value: '2.5M+', label: 'Messages scanned daily' },
  { value: '40k+', label: 'Communities protected' },
  { value: '180ms', label: 'Median action time' },
  { value: '99.99%', label: 'Uptime' },
]

const TESTIMONIALS = [
  { quote: 'Docket caught a 300-account raid before a single message landed in general. Our mods woke up to a clean log instead of a cleanup.', name: 'Sarah Chen', title: 'Head Moderator, The Nexus' },
  { quote: 'The case system replaced a messy spreadsheet and three bots. Every mod sees the full history the moment they open a member.', name: 'Marcus Reid', title: 'Server Owner, Forge & Anvil' },
  { quote: 'Appeals finally feel fair. The queue keeps every decision consistent, and members can see we actually reviewed them.', name: 'Priya Nair', title: 'Community Manager, Vela' },
  { quote: 'Automod scoring cut our workload in half. The team spends time on people now, not deleting spam links.', name: 'Diego Santos', title: 'Head Mod, Kite Lounge' },
  { quote: 'The watchlist flags repeat offenders across alt accounts. We stop problems days before they escalate.', name: 'Emma Wagner', title: 'Owner, Nova Collective' },
  { quote: 'Roles map exactly to how our team works — Helpers triage, Mods act, Admins configure. Onboarding takes minutes.', name: 'Kai Fischer', title: 'Admin, Drift Guild' },
]

export default function LandingPage() {
  return (
    <>
      {/* Hero — the records desk. Editorial headline + a live docket sheet. */}
      <section className="relative overflow-hidden border-b border-border">
        <div className="pointer-events-none absolute inset-0 -z-10 grid-texture opacity-60" />
        <div className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-px bg-accent-line" />
        <div className="mx-auto grid max-w-6xl items-center gap-14 px-6 py-20 lg:grid-cols-[1.05fr_1fr] lg:py-28">
          <div>
            <p className="inline-flex items-center gap-2 rounded-sm border border-border bg-surface px-3 py-1 font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.16em] text-accent">
              <span className="size-1.5 rounded-full bg-accent" />
              Moderation records desk
            </p>

            <h1 className="mt-6 font-display text-[3.25rem] font-semibold leading-[0.98] tracking-[-0.03em] text-foreground sm:text-[4rem]">
              Work your<br />caseload.
            </h1>
            <p className="mt-6 max-w-md text-lg leading-relaxed text-muted">
              Docket turns raids, spam, and reports into a clean queue of cases — each one filed,
              attributable, and resolved on the record. Moderation your whole team can read back.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link
                href="/api/auth/discord/authorize"
                className={buttonVariants({ variant: 'primary', size: 'lg', className: 'gap-2.5 px-7' })}
              >
                <LogIn className="size-4" />
                Sign in with Discord
              </Link>
              <Link
                href="#features"
                className={buttonVariants({ variant: 'outline', size: 'lg', className: 'gap-2' })}
              >
                See how it works
                <ArrowRight className="size-4" />
              </Link>
            </div>

            <p className="mt-5 font-mono text-[0.6875rem] uppercase tracking-[0.14em] text-muted-2">
              Free under 5k members · No card required
            </p>
          </div>

          <div className="relative lg:pl-4">
            <HeroPreview />
          </div>
        </div>
      </section>

      {/* Stats — a ledger strip. */}
      <section className="border-b border-border bg-surface">
        <div className="mx-auto grid max-w-6xl grid-cols-2 divide-x divide-y divide-border sm:grid-cols-4 sm:divide-y-0">
          {STATS.map((s) => (
            <div key={s.label} className="px-6 py-7">
              <div className="font-display text-3xl font-semibold tracking-tight text-foreground">{s.value}</div>
              <div className="mt-1 text-sm text-muted">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features — filed as records, each with a mono tag. */}
      <section id="features" className="mx-auto max-w-6xl scroll-mt-20 px-6 py-24">
        <div className="max-w-2xl">
          <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">
            What’s on the desk
          </p>
          <h2 className="mt-3 font-display text-4xl font-semibold tracking-[-0.02em] text-foreground">
            Everything a shift needs.<br />Nothing it doesn’t.
          </h2>
        </div>

        <div className="mt-12 grid gap-px overflow-hidden rounded-lg border border-border bg-border md:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.tag} className="group flex flex-col bg-surface p-7 transition-colors hover:bg-surface-2">
              <div className="flex items-center justify-between">
                <span className="grid size-9 place-items-center rounded-md bg-accent-soft text-accent">
                  <f.icon className="size-4.5" />
                </span>
                <span className="font-mono text-[0.625rem] font-semibold uppercase tracking-[0.16em] text-muted-2">
                  {f.tag}
                </span>
              </div>
              <h3 className="mt-5 font-display text-lg font-semibold tracking-tight text-foreground">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Testimonials — filed quotes. */}
      <section id="testimonials" className="border-y border-border bg-surface py-20">
        <div className="mx-auto max-w-6xl px-6">
          <p className="mb-10 font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-muted-2">
            On the record
          </p>
          <div className="grid gap-px overflow-hidden rounded-lg border border-border bg-border md:grid-cols-2 lg:grid-cols-3">
            {TESTIMONIALS.map((t) => (
              <figure key={t.name} className="flex flex-col justify-between bg-surface p-7">
                <blockquote className="rail rail-accent text-[15px] leading-snug text-foreground">
                  {t.quote}
                </blockquote>
                <figcaption className="mt-6 flex items-center gap-3">
                  <div className="grid size-8 place-items-center rounded-md bg-accent-soft font-display text-xs font-semibold text-accent">
                    {t.name.split(' ').map((w) => w[0]).join('')}
                  </div>
                  <div className="text-sm">
                    <div className="font-medium text-foreground">{t.name}</div>
                    <div className="text-xs text-muted">{t.title}</div>
                  </div>
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>

      <Pricing />
      <Faq />

      {/* Final CTA */}
      <section className="mx-auto max-w-4xl px-6 pb-24 pt-16 text-center">
        <h2 className="font-display text-4xl font-semibold tracking-[-0.02em] text-foreground">
          Open your first case.
        </h2>
        <p className="mx-auto mt-4 max-w-md text-lg text-muted">
          Sign in with Discord and add Docket to your server in under 60 seconds.
        </p>
        <div className="mt-8 flex justify-center">
          <Link
            href="/api/auth/discord/authorize"
            className={buttonVariants({ variant: 'primary', size: 'lg', className: 'gap-2.5 px-8' })}
          >
            <LogIn className="size-4.5" /> Sign in with Discord
          </Link>
        </div>
      </section>
    </>
  )
}
