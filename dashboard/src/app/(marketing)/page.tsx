import Link from 'next/link'
import {
  BarChart3,
  Users,
  ShieldCheck,
  Zap,
  LayoutDashboard,
  Bell,
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
  { icon: BarChart3, title: 'Real-time analytics', desc: 'Revenue, growth, retention, and conversion metrics that update as your business moves — with custom date ranges and switchable chart types.' },
  { icon: LayoutDashboard, title: 'Fully configurable', desc: 'Reorder widgets, hide what you don’t need, pick chart types, themes, accent colors, and layout density. Every preference is saved to your account.' },
  { icon: Users, title: 'Customer intelligence', desc: 'A complete view of every customer and account — plans, MRR, status, and activity — with server-side search, filters, and sorting.' },
  { icon: ShieldCheck, title: 'Roles & permissions', desc: 'Admin, Manager, and Viewer roles with an editable permission matrix. Access is enforced in the UI and on every API route.' },
  { icon: Bell, title: 'Notifications & audit', desc: 'A built-in notification center, activity feed, and immutable audit log so nothing important slips through the cracks.' },
  { icon: Zap, title: 'Built to scale', desc: 'A clean API layer and typed data models. Start on SQLite, move to Postgres, and connect real data sources without rewrites.' },
]

const STATS = [
  { value: '12M+', label: 'Events tracked daily' },
  { value: '4,200+', label: 'Teams onboard' },
  { value: '99.99%', label: 'Uptime SLA' },
  { value: '<50ms', label: 'Median query time' },
]

const TESTIMONIALS = [
  { quote: 'Nebula replaced three separate tools for us. The configurability means every team sees exactly the dashboard they need.', name: 'Sarah Chen', title: 'VP Growth, Loop', color: '#6366f1' },
  { quote: 'The permission system is the best I’ve used. We rolled out to 40 people across departments in an afternoon.', name: 'Marcus Reid', title: 'COO, Fathom', color: '#0ea5e9' },
  { quote: 'Finally an analytics product that our non-technical team actually enjoys using. The saved views are a game changer.', name: 'Priya Nair', title: 'Head of Ops, Vela', color: '#10b981' },
  { quote: 'We went from spreadsheets to real-time revenue tracking in a day. The audit log alone paid for itself.', name: 'Diego Santos', title: 'Founder, Kite', color: '#f43f5e' },
  { quote: 'Beautiful, fast, and thoughtfully built. Dark mode and accent colors make it feel like ours.', name: 'Emma Wagner', title: 'Design Lead, Nova', color: '#8b5cf6' },
  { quote: 'The API abstraction made connecting our warehouse trivial. Engineering loved how clean it was.', name: 'Kai Fischer', title: 'Staff Eng, Drift', color: '#f59e0b' },
]

export default function LandingPage() {
  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden">
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
              New: AI-powered anomaly detection
            </span>
            <h1 className="mt-5 text-4xl font-bold tracking-tight text-foreground sm:text-5xl lg:text-6xl">
              Every metric that matters, in one place
            </h1>
            <p className="mt-5 max-w-xl text-lg text-muted">
              Nebula is the analytics and operations platform for modern SaaS teams. Track revenue,
              understand customers, and give everyone a dashboard built exactly for them.
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
              14-day free trial · No credit card required · Cancel anytime
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
            Everything your team needs to operate
          </h2>
          <p className="mt-4 text-lg text-muted">
            A complete toolkit for analytics, customer management, and team operations — designed to
            be configured, not compromised.
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
              A dashboard that adapts to every role
            </h2>
            <p className="mt-4 text-lg text-muted">
              From the CEO tracking MRR to the analyst deep in retention cohorts, everyone gets a
              view built for them — without a single line of code.
            </p>
            <ul className="mt-6 space-y-3">
              {[
                'Drag-free widget management: show, hide, and reorder',
                'Per-widget chart types and global date ranges',
                'Themes, accent colors, and layout density',
                'Saved views with filters, sorting, and columns',
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
            Loved by teams everywhere
          </h2>
          <p className="mt-4 text-lg text-muted">
            Thousands of teams rely on Nebula to run their business every day.
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
            Ready to see everything in one place?
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-lg text-muted">
            Join thousands of teams running their business on Nebula. Get started in minutes.
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
