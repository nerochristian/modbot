import Link from 'next/link'
import {
  ArrowRight,
  Bell,
  Blocks,
  Check,
  ChevronDown,
  Crown,
  FileText,
  Gem,
  LockKeyhole,
  MessageSquare,
  Radar,
  Scale,
  ScrollText,
  Search,
  Settings,
  ShieldCheck,
  Siren,
  SlidersHorizontal,
  Sparkles,
  Star,
  TrendingUp,
  Users,
  Zap,
} from 'lucide-react'
import { buttonVariants } from '@/components/ui/button'
import { Logo } from '@/components/logo'
import { cn } from '@/lib/utils'

/**
 * The midnight storefront — dark SaaS landing page for Docket.
 *
 * Structure follows the classic bot-landing template: glowing console
 * mockup hero, stat strip, trust logos, feature card grid, dashboard
 * insights, pricing tiers, testimonials, FAQ, aurora CTA band. All
 * server-rendered; the only interactivity is native <details>.
 */

/* ---------------------------------------------------------------- */
/* Bits                                                             */

function Spark({ points, className }: { points: string; className?: string }) {
  return (
    <svg viewBox="0 0 80 24" preserveAspectRatio="none" aria-hidden className={cn('h-6 w-full', className)}>
      <polyline
        points={points}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function Stars({ className }: { className?: string }) {
  return (
    <span className={cn('flex items-center gap-0.5 text-warning', className)} aria-hidden>
      {Array.from({ length: 5 }, (_, i) => (
        <Star key={i} className="size-4 fill-current" />
      ))}
    </span>
  )
}

/* ---------------------------------------------------------------- */
/* Hero console mockup                                              */

const MOCK_NAV = [
  { label: 'Overview', icon: Radar, active: true },
  { label: 'Automod', icon: ShieldCheck },
  { label: 'Cases', icon: FileText, badge: '13' },
  { label: 'Members', icon: Users },
  { label: 'Appeals', icon: Scale },
  { label: 'Settings', icon: Settings },
]

const MOCK_STATS = [
  { label: 'Messages scanned', value: '7.2M', delta: '+12.5%', spark: '0,20 12,16 24,18 36,10 48,12 60,6 72,8 80,3' },
  { label: 'Automod actions', value: '24,510', delta: '+18.6%', spark: '0,18 12,20 24,14 36,16 48,9 60,12 72,6 80,4' },
  { label: 'Members protected', value: '128,450', delta: '+9.7%', spark: '0,16 12,14 24,15 36,11 48,13 60,8 72,9 80,5' },
]

const MOCK_EVENTS = [
  { text: 'Spam detected', where: '#general', when: '2s', tone: 'var(--danger)' },
  { text: 'Invite link blocked', where: '#memes', when: '15s', tone: 'var(--warning)' },
  { text: 'Suspected raid held', where: '#welcome', when: '1m', tone: 'var(--danger)' },
  { text: 'Bad word filtered', where: '#general', when: '2m', tone: 'var(--warning)' },
  { text: 'Mass mention stopped', where: '#trades', when: '3m', tone: 'var(--danger)' },
]

const MOCK_QUEUE = [
  { label: 'Ban evasion', user: 'alt_account123', when: '5m' },
  { label: 'Harassment', user: 'ToxicUser', when: '8m' },
  { label: 'Spam', user: 'PromoGuy', when: '11m' },
]

function ConsoleMock() {
  return (
    <div className="relative" id="dashboard">
      <p className="sr-only">
        Preview of the Docket dashboard: automod events, the moderation queue, and server health
        at a glance.
      </p>
      <div aria-hidden className="glow-frame overflow-hidden rounded-2xl bg-card text-left">
        <div className="grid lg:grid-cols-[11.5rem_1fr]">
          {/* Sidebar */}
          <div className="hidden flex-col border-r border-border bg-surface p-3 lg:flex">
            <Logo size="sm" />
            <div className="mt-4 rounded-lg border border-border bg-surface-2 px-2.5 py-2">
              <p className="text-xs font-semibold">Gaming Hub</p>
              <p className="mt-0.5 flex items-center gap-1.5 text-[0.625rem] text-muted-2">
                <span className="size-1.5 rounded-full bg-success" />
                1,234 online
              </p>
            </div>
            <ul className="mt-3 space-y-0.5">
              {MOCK_NAV.map((item) => (
                <li
                  key={item.label}
                  className={cn(
                    'flex items-center gap-2 rounded-md px-2.5 py-1.5 text-xs',
                    item.active ? 'bg-accent-soft font-semibold text-accent' : 'text-muted',
                  )}
                >
                  <item.icon className="size-3.5" />
                  {item.label}
                  {item.badge && (
                    <span className="ml-auto rounded-full bg-accent px-1.5 text-[0.625rem] font-semibold text-accent-foreground">
                      {item.badge}
                    </span>
                  )}
                </li>
              ))}
            </ul>
            <div className="mt-auto flex items-center gap-2 rounded-lg border border-border px-2.5 py-2">
              <span className="flex size-6 items-center justify-center rounded-full bg-aurora text-[0.625rem] font-bold text-white">
                M
              </span>
              <div>
                <p className="text-[0.6875rem] font-semibold">ModMaster</p>
                <p className="text-[0.625rem] text-muted-2">#0001</p>
              </div>
            </div>
          </div>

          {/* Main */}
          <div className="p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold">Overview</p>
              <div className="flex items-center gap-2 text-muted-2">
                <Search className="size-3.5" />
                <Bell className="size-3.5" />
                <span className="rounded-md border border-border px-2 py-1 font-mono text-[0.625rem]">
                  Jul 13 – Jul 20
                </span>
              </div>
            </div>

            {/* Stat cards */}
            <div className="mt-3 grid grid-cols-3 gap-2">
              {MOCK_STATS.map((stat) => (
                <div key={stat.label} className="rounded-lg border border-border bg-surface p-2.5">
                  <p className="truncate text-[0.625rem] text-muted-2">{stat.label}</p>
                  <p className="mt-1 flex items-baseline gap-1.5">
                    <span className="mono-id text-base font-semibold">{stat.value}</span>
                    <span className="text-[0.625rem] font-semibold text-success">{stat.delta}</span>
                  </p>
                  <Spark points={stat.spark} className="mt-1.5 text-accent" />
                </div>
              ))}
            </div>

            {/* Panels */}
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              <div className="rounded-lg border border-border bg-surface p-2.5">
                <p className="mb-2 flex items-center justify-between text-[0.6875rem] font-semibold">
                  Automod events
                  <span className="font-normal text-muted-2">View all</span>
                </p>
                <ul className="space-y-1.5">
                  {MOCK_EVENTS.map((event) => (
                    <li key={event.text} className="flex items-center gap-2 text-[0.6875rem]">
                      <span className="size-1.5 shrink-0 rounded-full" style={{ background: event.tone }} />
                      <span className="truncate text-muted">{event.text}</span>
                      <span className="text-muted-2">{event.where}</span>
                      <span className="ml-auto shrink-0 font-mono text-[0.625rem] text-muted-2">
                        {event.when}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="flex flex-col rounded-lg border border-border bg-surface p-2.5">
                <p className="mb-2 text-[0.6875rem] font-semibold">
                  Moderation queue
                  <span className="ml-2 rounded-full bg-danger-soft px-1.5 py-0.5 text-[0.625rem] font-semibold text-danger">
                    3 pending
                  </span>
                </p>
                <ul className="space-y-1.5">
                  {MOCK_QUEUE.map((item) => (
                    <li key={item.label} className="flex items-center gap-2 text-[0.6875rem]">
                      <Siren className="size-3 shrink-0 text-danger" />
                      <span className="text-muted">{item.label}</span>
                      <span className="mono-id truncate text-muted-2">@{item.user}</span>
                      <span className="ml-auto shrink-0 font-mono text-[0.625rem] text-muted-2">
                        {item.when}
                      </span>
                    </li>
                  ))}
                </ul>
                <span className="mt-auto rounded-md border border-border py-1.5 pt-1.5 text-center text-[0.6875rem] font-medium text-muted">
                  Review queue
                </span>
              </div>
            </div>

            {/* Health strip */}
            <div className="mt-2 grid grid-cols-4 gap-2">
              {[
                { label: 'Uptime', value: '99.99%' },
                { label: 'Audit logs', value: '1.2K' },
                { label: 'Compliance', value: '98%' },
                { label: 'Response', value: '320ms' },
              ].map((cell) => (
                <div key={cell.label} className="rounded-lg border border-border bg-surface px-2.5 py-2">
                  <p className="text-[0.625rem] text-muted-2">{cell.label}</p>
                  <p className="mono-id mt-0.5 text-xs font-semibold text-success">{cell.value}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ---------------------------------------------------------------- */
/* Copy                                                             */

const HERO_STATS = [
  { icon: Users, value: '12K+', label: 'Servers' },
  { icon: ShieldCheck, value: '2.1M+', label: 'Members protected' },
  { icon: Zap, value: '99.99%', label: 'Uptime' },
  { icon: Star, value: '4.9 / 5', label: 'From 1.2K+ reviews' },
]

const TRUSTED = [
  { name: 'Phase', icon: Zap },
  { name: 'Elevate', icon: TrendingUp },
  { name: 'Nexus', icon: Blocks },
  { name: 'Frontier', icon: Gem },
  { name: 'Infinity', icon: Crown },
]

const FEATURES = [
  {
    icon: ShieldCheck,
    name: 'AutoMod',
    body: 'Rule-based automation that works 24/7 to stop problems before your mods see them.',
  },
  {
    icon: Siren,
    name: 'Anti-spam & raids',
    body: 'Stops spam bursts, invite links, mass mentions, and raid patterns in real time.',
  },
  {
    icon: FileText,
    name: 'Case files',
    body: 'Every action becomes a numbered, searchable case with the evidence attached.',
  },
  {
    icon: Scale,
    name: 'Appeals & tickets',
    body: 'Built-in appeal forms and ticket flows, decided with the full record in view.',
  },
  {
    icon: Users,
    name: 'Member ledger',
    body: 'Standing, risk level, and complete history for every member of your server.',
  },
  {
    icon: ScrollText,
    name: 'Logging',
    body: 'Comprehensive, searchable logs for every action and everyone, exportable anytime.',
  },
  {
    icon: LockKeyhole,
    name: 'Team & roles',
    body: 'Admin, Moderator, Helper — a permission matrix that mirrors your Discord roles.',
  },
  {
    icon: SlidersHorizontal,
    name: 'Custom rules',
    body: 'Flexible conditions, punishments, thresholds, exemptions, and cooldowns.',
  },
]

const INSIGHTS = [
  'Real-time analytics',
  'Customizable widgets',
  'Exportable reports',
  'Team workload insights',
]

const TOP_RULES = [
  { name: 'Invite links', pct: 76 },
  { name: 'Spam burst', pct: 58 },
  { name: 'Bad words', pct: 41 },
  { name: 'Mass mention', pct: 24 },
]

const PLANS = [
  {
    name: 'Free',
    price: '$0',
    period: 'forever',
    blurb: 'For small communities getting started.',
    features: ['Basic automod rules', 'Case files & member ledger', '7-day evidence retention', '2 custom rules'],
    cta: 'Add to server',
    highlight: false,
  },
  {
    name: 'Premium',
    price: '$6.99',
    period: '/month',
    blurb: 'Powerful tools for growing communities.',
    features: [
      'Advanced automod & anti-raid',
      'Appeals & tickets',
      '90-day evidence retention',
      'Unlimited custom rules',
      'Priority support',
    ],
    cta: 'Get Premium',
    highlight: true,
  },
  {
    name: 'Elite',
    price: '$14.99',
    period: '/month',
    blurb: 'For large communities that need it all.',
    features: [
      'Everything in Premium',
      '1-year evidence retention',
      'Advanced analytics',
      'Custom commands',
      'Dedicated support',
    ],
    cta: 'Get Elite',
    highlight: false,
  },
]

const QUOTES = [
  {
    text: 'Docket has completely transformed how we moderate. Every decision has a paper trail, and the dashboard is a dream.',
    name: 'Vortex',
    role: 'Community Manager',
  },
  {
    text: 'Best moderation bot we’ve ever used. The appeals desk alone saves our mod team hours every single week.',
    name: 'Apex Community',
    role: '340K members',
  },
  {
    text: 'Reliable, fast, and packed with features. The case system ended every “who banned this guy and why” argument forever.',
    name: 'Nebula Studios',
    role: 'Gaming network',
  },
]

const FAQ = [
  {
    q: 'Is Docket easy to set up?',
    a: 'Yes — invite the bot, authorize with Discord, and switch on the automod rules you want. Sensible defaults are included, and the desk is working within about two minutes.',
  },
  {
    q: 'Does Docket store message content?',
    a: 'Only content purged by a rule is retained, as case evidence. It is visible solely to your moderation team and can be erased per-case or server-wide at any time.',
  },
  {
    q: 'Can I customize the bot?',
    a: 'Absolutely. Create custom rules with your own conditions, punishments, thresholds, exempt roles, and cooldowns — and tune every automod filter per channel.',
  },
  {
    q: 'Is there a limit to server size?',
    a: 'No. Docket scales with your community, whether you have 50 members or 500,000 — and the permission matrix keeps a large mod team organized.',
  },
]

/* ---------------------------------------------------------------- */
/* Page                                                             */

export default function LandingPage() {
  return (
    <div className="overflow-x-clip">
      {/* ============================================================ */}
      {/* Hero                                                         */}
      <section className="mx-auto grid max-w-7xl items-center gap-12 px-4 pt-14 pb-16 sm:px-6 lg:grid-cols-[0.95fr_1.05fr] lg:gap-10 lg:pt-20">
        <div className="space-y-7">
          <p className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3.5 py-1.5 text-xs font-medium text-muted">
            <Sparkles className="size-3.5 text-accent" aria-hidden />
            The #1 moderation desk for Discord
          </p>
          <h1 className="font-display text-4xl leading-[1.04] font-semibold tracking-tight text-balance sm:text-5xl lg:text-[3.4rem]">
            Powerful moderation <br className="hidden sm:block" />
            for <span className="text-aurora">modern communities</span>
          </h1>
          <p className="max-w-lg text-lg leading-8 text-muted">
            Docket keeps your server safe, organized, and thriving with advanced automod, real
            case files, built-in appeals, and beautiful analytics — so you can focus on your
            community.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Link href="/register" className={buttonVariants({ size: 'lg' })}>
              <MessageSquare className="size-4" aria-hidden />
              Add to server
            </Link>
            <Link href="/login" className={buttonVariants({ variant: 'secondary', size: 'lg' })}>
              View dashboard
              <ArrowRight className="size-4" aria-hidden />
            </Link>
          </div>

          <dl className="grid max-w-lg grid-cols-2 gap-x-6 gap-y-4 border-t border-border pt-6 sm:grid-cols-4">
            {HERO_STATS.map((stat) => (
              <div key={stat.label} className="flex items-start gap-2">
                <stat.icon className="mt-0.5 size-4 shrink-0 text-accent" aria-hidden />
                <div>
                  <dt className="sr-only">{stat.label}</dt>
                  <dd className="text-sm font-bold">{stat.value}</dd>
                  <dd className="text-[0.6875rem] leading-4 text-muted-2">{stat.label}</dd>
                </div>
              </div>
            ))}
          </dl>

          <div>
            <p className="text-xs text-muted-2">Trusted by communities worldwide</p>
            <div className="mt-3 flex flex-wrap items-center gap-x-7 gap-y-3 opacity-60">
              {TRUSTED.map((brand) => (
                <span
                  key={brand.name}
                  className="flex items-center gap-1.5 text-sm font-semibold tracking-[0.18em] uppercase"
                >
                  <brand.icon className="size-4" aria-hidden />
                  {brand.name}
                </span>
              ))}
            </div>
          </div>
        </div>

        <ConsoleMock />
      </section>

      {/* ============================================================ */}
      {/* Features                                                     */}
      <section id="features" className="scroll-mt-20 border-t border-border">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
          <h2 className="text-center font-display text-3xl tracking-tight text-balance sm:text-4xl">
            Everything you need to protect and grow your community
          </h2>
          <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map((feature) => (
              <div key={feature.name} className="card-glow rounded-xl border border-border bg-card p-5">
                <span className="inline-flex size-10 items-center justify-center rounded-lg bg-accent-soft text-accent">
                  <feature.icon className="size-5" aria-hidden />
                </span>
                <h3 className="mt-4 font-semibold">{feature.name}</h3>
                <p className="mt-1.5 text-sm leading-6 text-muted">{feature.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============================================================ */}
      {/* Insights                                                     */}
      <section className="border-t border-border">
        <div className="mx-auto grid max-w-7xl items-center gap-12 px-4 py-20 sm:px-6 lg:grid-cols-2">
          <div className="space-y-6">
            <h2 className="font-display text-3xl tracking-tight text-balance sm:text-4xl">
              Detailed insights. <span className="text-aurora">Smarter moderation.</span>
            </h2>
            <p className="max-w-md text-base leading-7 text-muted">
              Docket&rsquo;s dashboard gives you the clarity and control you need, with real-time
              analytics, actionable insights, and easy-to-use tools for your whole team.
            </p>
            <ul className="space-y-3">
              {INSIGHTS.map((item) => (
                <li key={item} className="flex items-center gap-2.5 text-sm">
                  <span className="flex size-5 items-center justify-center rounded-full bg-success-soft text-success">
                    <Check className="size-3" aria-hidden />
                  </span>
                  {item}
                </li>
              ))}
            </ul>
            <Link href="/register" className={buttonVariants({ variant: 'secondary' })}>
              Explore dashboard
              <ArrowRight className="size-4" aria-hidden />
            </Link>
          </div>

          {/* Analytics mockup */}
          <div aria-hidden className="glow-frame rounded-2xl bg-card p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold">Activity overview</p>
              <span className="rounded-md border border-border px-2 py-1 font-mono text-[0.625rem] text-muted-2">
                Last 30 days
              </span>
            </div>
            <div className="mt-4 flex h-28 items-end gap-1.5">
              {[38, 52, 44, 66, 58, 74, 60, 82, 70, 92, 78, 96].map((height, i) => (
                <div
                  key={i}
                  className={cn('flex-1 rounded-t', i === 11 ? 'bg-aurora' : 'bg-accent-soft')}
                  style={{ height: `${height}%` }}
                />
              ))}
            </div>
            <div className="mt-5 border-t border-border pt-4">
              <p className="mb-3 text-xs font-semibold text-muted">Top triggered rules</p>
              <ul className="space-y-2.5">
                {TOP_RULES.map((rule) => (
                  <li key={rule.name} className="flex items-center gap-3 text-xs">
                    <span className="w-24 shrink-0 text-muted">{rule.name}</span>
                    <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-2">
                      <span className="block h-full rounded-full bg-aurora" style={{ width: `${rule.pct}%` }} />
                    </span>
                    <span className="mono-id w-8 text-right text-muted-2">{rule.pct}%</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ============================================================ */}
      {/* Pricing                                                      */}
      <section id="pricing" className="scroll-mt-20 border-t border-border">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
          <h2 className="text-center font-display text-3xl tracking-tight sm:text-4xl">
            Simple, transparent pricing
          </h2>
          <div className="mx-auto mt-6 flex w-fit items-center rounded-full border border-border bg-surface p-1 text-xs font-medium">
            <span className="rounded-full bg-accent px-4 py-1.5 text-accent-foreground">Monthly</span>
            <span className="px-4 py-1.5 text-muted">Yearly (20% off)</span>
          </div>

          <div className="mt-10 grid items-stretch gap-5 lg:grid-cols-3">
            {PLANS.map((plan) => (
              <div
                key={plan.name}
                className={cn(
                  'relative flex flex-col rounded-2xl border bg-card p-6',
                  plan.highlight ? 'glow-frame' : 'border-border',
                )}
              >
                {plan.highlight && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-aurora px-3 py-1 text-[0.6875rem] font-semibold text-white">
                    Most popular
                  </span>
                )}
                <h3 className="font-semibold">{plan.name}</h3>
                <p className="mt-2 flex items-baseline gap-1">
                  <span className="font-display text-4xl font-semibold tracking-tight">{plan.price}</span>
                  <span className="text-sm text-muted-2">{plan.period}</span>
                </p>
                <p className="mt-2 text-sm text-muted">{plan.blurb}</p>
                <ul className="mt-5 space-y-2.5 border-t border-border pt-5">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2.5 text-sm text-muted">
                      <Check className="mt-0.5 size-4 shrink-0 text-success" aria-hidden />
                      {feature}
                    </li>
                  ))}
                </ul>
                <Link
                  href="/register"
                  className={cn(
                    buttonVariants({ variant: plan.highlight ? 'primary' : 'outline' }),
                    'mt-6',
                  )}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
          <p className="mt-6 text-center text-xs text-muted-2">
            All paid plans include a 14-day free trial. Cancel anytime.
          </p>
        </div>
      </section>

      {/* ============================================================ */}
      {/* Testimonials                                                 */}
      <section className="border-t border-border">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
          <div className="flex flex-col items-center gap-2 text-center">
            <h2 className="font-display text-3xl tracking-tight sm:text-4xl">
              Loved by thousands of communities
            </h2>
            <p className="mt-1 flex items-center gap-2.5 text-sm text-muted">
              <Stars />
              <span className="font-semibold text-foreground">4.9/5</span> based on 1,200+ reviews
            </p>
          </div>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {QUOTES.map((quote) => (
              <figure key={quote.name} className="card-glow flex flex-col rounded-xl border border-border bg-card p-6">
                <Stars className="mb-4" />
                <blockquote className="text-sm leading-7 text-muted">
                  &ldquo;{quote.text}&rdquo;
                </blockquote>
                <figcaption className="mt-5 flex items-center gap-3 border-t border-border pt-4">
                  <span className="flex size-8 items-center justify-center rounded-full bg-aurora text-xs font-bold text-white">
                    {quote.name[0]}
                  </span>
                  <span>
                    <span className="block text-sm font-semibold">{quote.name}</span>
                    <span className="block text-xs text-muted-2">{quote.role}</span>
                  </span>
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>

      {/* ============================================================ */}
      {/* FAQ                                                          */}
      <section id="faq" className="scroll-mt-20 border-t border-border">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
          <h2 className="text-center font-display text-3xl tracking-tight sm:text-4xl">
            Frequently asked questions
          </h2>
          <div className="mt-10 grid gap-4 md:grid-cols-2">
            {FAQ.map((item) => (
              <details key={item.q} className="group rounded-xl border border-border bg-card px-5">
                <summary className="focus-ring flex cursor-pointer list-none items-center justify-between gap-4 rounded-xl py-4 text-sm font-semibold [&::-webkit-details-marker]:hidden">
                  {item.q}
                  <ChevronDown
                    className="size-4 shrink-0 text-muted-2 transition-transform group-open:rotate-180"
                    aria-hidden
                  />
                </summary>
                <p className="pb-5 text-sm leading-7 text-muted">{item.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ============================================================ */}
      {/* CTA band                                                     */}
      <section className="bg-aurora">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 px-4 py-12 text-white sm:px-6 lg:flex-row">
          <div className="flex items-center gap-4 text-center lg:text-left">
            <span className="hidden size-12 shrink-0 items-center justify-center rounded-full border border-white/30 bg-white/10 sm:flex">
              <ShieldCheck className="size-6" aria-hidden />
            </span>
            <div>
              <h2 className="font-display text-2xl tracking-tight">
                Ready to build a safer, stronger community?
              </h2>
              <p className="mt-1 text-sm text-white/80">
                Join 12,000+ servers that trust Docket to protect what matters.
              </p>
            </div>
          </div>
          <Link
            href="/register"
            className={cn(
              buttonVariants({ size: 'lg' }),
              'shrink-0 bg-white text-[#1d4ed8] shadow-none hover:brightness-95',
            )}
          >
            <MessageSquare className="size-4" aria-hidden />
            Add Docket to your server
            <ArrowRight className="size-4" aria-hidden />
          </Link>
        </div>
      </section>
    </div>
  )
}
