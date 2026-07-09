import Link from 'next/link'
import {
  ShieldAlert,
  Gavel,
  Scale,
  Users2,
  SlidersHorizontal,
  Activity,
  Sparkles,
  ArrowRight,
  Star,
} from 'lucide-react'
import { buttonVariants } from '@/components/ui/button'
import { HeroPreview } from '@/components/marketing/hero-preview'
import { Pricing } from '@/components/marketing/pricing'
import { Faq } from '@/components/marketing/faq'
import { cn } from '@/lib/utils'

const FEATURES = [
  { icon: ShieldAlert, title: 'Automod rule builder', desc: 'Compose layered rules for spam, slurs, invite links, mention floods, and raid patterns. Every rule scores content in real time and acts before your team ever sees it.' },
  { icon: Gavel, title: 'Case & infraction tracking', desc: 'Every warn, mute, kick, and ban becomes a case with full history, evidence, and moderator notes. Nothing gets lost between shifts.' },
  { icon: Scale, title: 'Appeals workflow', desc: 'Members submit appeals through a structured queue your team reviews, votes on, and resolves — so punishments stay fair and consistent.' },
  { icon: Users2, title: 'Member intelligence', desc: 'A complete profile for every member — join date, prior infractions, risk signals, and watchlist status — with server-side search, filters, and sorting.' },
  { icon: SlidersHorizontal, title: 'Roles & permissions', desc: 'Admin, Moderator, and Helper roles with an editable permission matrix. Access is enforced in the command deck and on every API route.' },
  { icon: Activity, title: 'Configurable command deck', desc: 'Reorder widgets, hide what you don’t need, pick severity thresholds, themes, and layout density. Every preference is saved to your account.' },
]

const STATS = [
  { value: '2.5M+', label: 'Messages scanned daily' },
  { value: '40k+', label: 'Communities protected' },
  { value: '180ms', label: 'Median action time' },
  { value: '99.99%', label: 'Uptime' },
]

const TESTIMONIALS = [
  { quote: 'Aegis caught a 300-account raid before a single message landed in general. Our mods woke up to a clean log instead of a cleanup.', name: 'Sarah Chen', title: 'Head Moderator, The Nexus', color: '#6e56f8' },
  { quote: 'The case system replaced a messy spreadsheet and three bots. Every mod sees the full history the moment they open a member.', name: 'Marcus Reid', title: 'Server Owner, Forge & Anvil', color: '#0ea5e9' },
  { quote: 'Appeals finally feel fair. The queue keeps every decision consistent, and members can see we actually reviewed them.', name: 'Priya Nair', title: 'Community Manager, Vela', color: '#22c55e' },
  { quote: 'Automod scoring cut our mod workload in half. The team spends time on people now, not deleting spam links.', name: 'Diego Santos', title: 'Head Mod, Kite Lounge', color: '#f43f5e' },
  { quote: 'The watchlist flags repeat offenders across alt accounts. We stop problems days before they escalate.', name: 'Emma Wagner', title: 'Owner, Nova Collective', color: '#8b5cf6' },
  { quote: 'Roles map exactly to how our team works — Helpers triage, Mods act, Admins configure. Onboarding a new mod takes minutes.', name: 'Kai Fischer', title: 'Admin, Drift Guild', color: '#f59e0b' },
]

export default function LandingPage() {
  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="grid-texture pointer-events-none absolute inset-0 -z-10 opacity-40" />
        <div
          className="pointer-events-none absolute inset-0 -z-10 opacity-60"
          style={{
            background:
              'radial-gradient(60% 50% at 50% 0%, color-mix(in srgb, var(--accent) 18%, transparent), transparent 70%)',
          }}
        />
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-20 sm:px-6 lg:grid-cols-2 lg:py-28">
          <div>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-muted">
              <Sparkles className="size-3.5 text-accent" />
              New: AI content scoring
            </span>
            <h1 className="mt-5 text-4xl font-bold tracking-tight text-foreground sm:text-5xl lg:text-6xl">
              Keep your community safe at any scale
            </h1>
            <p className="mt-5 max-w-xl text-lg text-muted">
              Aegis is the moderation platform for serious Discord communities. Stop raids and spam
              automatically, track every case in one place, and give your whole mod team a command
              deck built exactly for how they work.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link href="/register" className={buttonVariants({ variant: 'primary', size: 'lg' })}>
                Start free trial
                <ArrowRight className="size-4" />
              </Link>
              <Link href="/login" className={buttonVariants({ variant: 'outline', size: 'lg' })}>
                Live demo
              </Link>
            </div>
            <p className="mt-4 text-sm text-muted-2">
              Add Aegis to your server in 2 minutes · No credit card required · Cancel anytime
            </p>
          </div>
          <div className="lg:pl-6">
            <HeroPreview />
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="border-y border-border bg-surface">
        <div className="mx-auto grid max-w-6xl grid-cols-2 gap-8 px-4 py-12 sm:px-6 lg:grid-cols-4">
          {STATS.map((s) => (
            <div key={s.label} className="text-center">
              <p className="text-3xl font-bold tracking-tight text-foreground">{s.value}</p>
              <p className="mt-1 text-sm text-muted">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-24 sm:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <span className="text-sm font-semibold text-accent">Features</span>
          <h2 className="mt-2 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            Everything your mod team needs to hold the line
          </h2>
          <p className="mt-4 text-lg text-muted">
            A complete toolkit for automod, cases, appeals, and member intelligence — designed to be
            configured, not compromised.
          </p>
        </div>
        <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="group rounded-2xl border border-border bg-card p-6 transition-colors hover:border-border-strong"
            >
              <span className="flex size-11 items-center justify-center rounded-xl bg-accent-soft text-accent">
                <f.icon className="size-5.5" />
              </span>
              <h3 className="mt-4 text-base font-semibold text-foreground">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Spotlight */}
      <section className="border-y border-border bg-surface">
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-24 sm:px-6 lg:grid-cols-2">
          <div>
            <span className="text-sm font-semibold text-accent">Configurable by design</span>
            <h2 className="mt-2 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              A command deck that adapts to every moderator
            </h2>
            <p className="mt-4 text-lg text-muted">
              From the owner watching raid signals to the helper triaging the appeals queue, everyone
              gets a view built for them — without a single line of code.
            </p>
            <ul className="mt-6 space-y-3">
              {[
                'Drag-free widget management: show, hide, and reorder',
                'Automod severity thresholds and per-rule actions',
                'Saved views with filters, sorting, and columns',
                'Watchlist and open-case widgets front and center',
                'Feature toggles and admin-controlled widget catalog',
              ].map((item) => (
                <li key={item} className="flex items-start gap-2.5 text-sm text-foreground">
                  <Star className="mt-0.5 size-4 shrink-0 text-accent" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <HeroPreview />
        </div>
      </section>

      {/* Testimonials */}
      <section id="testimonials" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-24 sm:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <span className="text-sm font-semibold text-accent">Testimonials</span>
          <h2 className="mt-2 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            Trusted by the mod teams that hold big servers together
          </h2>
          <p className="mt-4 text-lg text-muted">
            Thousands of communities rely on Aegis to stay safe every day.
          </p>
        </div>
        <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {TESTIMONIALS.map((t) => (
            <figure key={t.name} className="flex flex-col rounded-2xl border border-border bg-card p-6">
              <div className="flex gap-0.5 text-warning">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Star key={i} className="size-4 fill-current" />
                ))}
              </div>
              <blockquote className="mt-4 flex-1 text-sm leading-relaxed text-foreground">
                “{t.quote}”
              </blockquote>
              <figcaption className="mt-5 flex items-center gap-3">
                <span
                  className="flex size-9 items-center justify-center rounded-full text-sm font-semibold text-white"
                  style={{ backgroundColor: t.color }}
                >
                  {t.name.split(' ').map((n) => n[0]).join('')}
                </span>
                <div>
                  <p className="text-sm font-medium text-foreground">{t.name}</p>
                  <p className="text-xs text-muted">{t.title}</p>
                </div>
              </figcaption>
            </figure>
          ))}
        </div>
      </section>

      <Pricing />
      <Faq />

      {/* CTA */}
      <section className="mx-auto max-w-6xl px-4 pb-24 sm:px-6">
        <div
          className={cn(
            'relative overflow-hidden rounded-3xl border border-border px-6 py-16 text-center sm:px-16',
          )}
          style={{
            background:
              'linear-gradient(135deg, color-mix(in srgb, var(--accent) 16%, var(--surface)), var(--surface))',
          }}
        >
          <h2 className="mx-auto max-w-2xl text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            Ready to protect your community?
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-lg text-muted">
            Join thousands of communities keeping their members safe with Aegis. Add it to your
            server in minutes.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link href="/register" className={buttonVariants({ variant: 'primary', size: 'lg' })}>
              Start free trial
              <ArrowRight className="size-4" />
            </Link>
            <Link href="/login" className={buttonVariants({ variant: 'outline', size: 'lg' })}>
              Sign in
            </Link>
          </div>
        </div>
      </section>
    </>
  )
}
