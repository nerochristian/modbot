import Link from 'next/link'
import {
  ArrowRight,
  FileClock,
  LogIn,
  MessageSquareWarning,
  Settings2,
  ShieldCheck,
  TicketCheck,
  UsersRound,
} from 'lucide-react'
import { buttonVariants } from '@/components/ui/button'
import { LiveWire } from '@/components/marketing/live-wire'
import { CircuitField } from '@/components/marketing/circuit-field'
import { CommandDemo } from '@/components/marketing/command-demo'
import { Faq } from '@/components/marketing/faq'

const PRODUCT_AREAS = [
  { value: 'Automod', label: 'Stop harmful messages automatically' },
  { value: 'Cases', label: 'Keep every staff action on record' },
  { value: 'Reports', label: 'Give members a private way to report' },
  { value: 'Tickets', label: 'Run support in private channels' },
]

const FEATURES = [
  {
    icon: ShieldCheck,
    title: 'Automod you can control',
    body: 'Configure spam, links, invites, mention floods, blocked words, duplicate messages, and raid protection from one place.',
  },
  {
    icon: FileClock,
    title: 'Cases and member history',
    body: 'Warnings, timeouts, kicks, bans, reasons, evidence, and staff notes stay attached to the member who received them.',
  },
  {
    icon: MessageSquareWarning,
    title: 'Private member reports',
    body: 'Members or staff can use /report. Reports reach the moderation team without exposing the reporter in a public channel.',
  },
  {
    icon: TicketCheck,
    title: 'Tickets built around your server',
    body: 'Choose ticket options, questions, optional emoji, staff access, private channels, and transcript logging from the dashboard.',
  },
]

const SETUP = [
  {
    n: '01',
    title: 'Sign in with Discord',
    body: 'Docket uses your Discord account to identify you. Your Discord password always stays with Discord.',
  },
  {
    n: '02',
    title: 'Choose a server you administer',
    body: 'The dashboard only shows servers you own or where your live Discord permissions include Administrator.',
  },
  {
    n: '03',
    title: 'Configure how your team works',
    body: 'Turn modules on, choose channels and roles, build automod rules, and manage moderation from Discord or the dashboard.',
  },
]

const WORKFLOW = [
  {
    icon: UsersRound,
    title: 'Understand the member',
    body: 'Open a member to see their Discord identity, roles, recorded actions, cases, appeals, and staff notes together.',
  },
  {
    icon: Settings2,
    title: 'Take the right action',
    body: 'Warn, timeout, kick, ban, add a note, or review a report with the reason and result kept on the record.',
  },
  {
    icon: FileClock,
    title: 'Know what happened later',
    body: 'Cases, action logs, reports, and transcripts give the next moderator enough context to continue the work.',
  },
]

export default function LandingPage() {
  return (
    <>
      <section className="relative overflow-hidden border-b border-border">
        <CircuitField className="pointer-events-none absolute inset-0 h-full w-full opacity-70" />
        <div className="scanfield pointer-events-none absolute inset-0 opacity-40" />
        <div
          className="pointer-events-none absolute -left-32 top-0 h-[420px] w-[420px] rounded-full opacity-25 blur-[120px]"
          style={{ background: 'radial-gradient(circle, var(--brand-from), transparent 70%)' }}
        />
        <div
          className="pointer-events-none absolute -right-24 bottom-0 h-[380px] w-[380px] rounded-full opacity-20 blur-[120px]"
          style={{ background: 'radial-gradient(circle, var(--brand-cyan), transparent 70%)' }}
        />
        <div className="pointer-events-none absolute left-1/2 top-0 hidden h-full w-px bg-border lg:block" />

        <div className="relative mx-auto grid max-w-6xl items-center gap-x-12 gap-y-10 px-6 py-16 lg:grid-cols-[0.9fr_1.1fr] lg:py-20">
          <div>
            <p className="inline-flex items-center gap-2 rounded-sm border border-border bg-surface px-3 py-1 font-mono text-[0.6875rem] font-medium uppercase tracking-[0.16em] text-accent">
              <span className="inline-flex size-1.5 rounded-full bg-accent wire-blip" />
              Discord moderation dashboard
            </p>
            <h1 className="mt-6 font-display text-[2.75rem] font-semibold leading-[0.98] tracking-[-0.02em] text-foreground sm:text-6xl">
              Moderate your server.
              <br />
              <span className="text-brand-gradient">Keep the full record.</span>
            </h1>
            <p className="mt-6 max-w-lg text-lg leading-relaxed text-muted">
              Docket brings automod, cases, member reports, tickets, appeals, and staff actions into one dashboard connected to your Discord server.
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
                See what Docket does
                <ArrowRight className="size-4" />
              </Link>
            </div>
            <p className="mt-5 font-mono text-[0.6875rem] uppercase tracking-[0.14em] text-muted-2">
              Dashboard access requires live Discord Administrator permission
            </p>
          </div>

          <div className="lg:-mr-4">
            <div className="mb-3 flex items-center justify-between font-mono text-[0.625rem] uppercase tracking-[0.14em] text-muted-2">
              <span>Example automod response</span>
              <span>Preview data</span>
            </div>
            <LiveWire />
          </div>
        </div>
      </section>

      <section className="border-b border-border bg-surface">
        <div className="mx-auto grid max-w-6xl grid-cols-2 divide-x divide-y divide-border sm:grid-cols-4 sm:divide-y-0">
          {PRODUCT_AREAS.map((area) => (
            <div key={area.value} className="px-6 py-7">
              <div className="font-display text-xl font-semibold tracking-tight text-foreground">{area.value}</div>
              <div className="mt-1.5 text-sm leading-snug text-muted">{area.label}</div>
            </div>
          ))}
        </div>
      </section>

      <section id="features" className="mx-auto max-w-6xl scroll-mt-20 px-6 py-20">
        <div className="max-w-2xl">
          <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">
            One place for the moderation team
          </p>
          <h2 className="mt-3 font-display text-4xl font-semibold tracking-[-0.02em] text-foreground">
            The tools your server actually uses.
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted">
            Configure the bot, review what happened, and act on members without searching through old channels or disconnected commands.
          </p>
        </div>

        <div className="mt-12 grid gap-px overflow-hidden rounded-lg border border-border bg-border md:grid-cols-2">
          {FEATURES.map((feature) => {
            const Icon = feature.icon
            return (
              <article key={feature.title} className="bg-surface p-7 sm:p-8">
                <span className="grid size-10 place-items-center rounded-md border border-accent-line bg-accent-soft text-accent">
                  <Icon className="size-5" />
                </span>
                <h3 className="mt-5 font-display text-xl font-semibold tracking-tight text-foreground">{feature.title}</h3>
                <p className="mt-2.5 text-sm leading-relaxed text-muted">{feature.body}</p>
              </article>
            )
          })}
        </div>
      </section>

      <section id="setup" className="border-y border-border bg-surface">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <div className="max-w-2xl">
            <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">
              How setup works
            </p>
            <h2 className="mt-3 font-display text-4xl font-semibold tracking-[-0.02em] text-foreground">
              From Discord to your dashboard in three steps.
            </h2>
          </div>

          <div className="mt-12 grid gap-px overflow-hidden rounded-lg border border-border bg-border md:grid-cols-3">
            {SETUP.map((step) => (
              <article key={step.n} className="bg-card p-7">
                <span className="font-mono text-sm font-semibold text-accent">{step.n}</span>
                <h3 className="mt-5 font-display text-xl font-semibold tracking-tight text-foreground">{step.title}</h3>
                <p className="mt-2.5 text-sm leading-relaxed text-muted">{step.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="members" className="border-b border-border">
        <div className="mx-auto grid max-w-6xl scroll-mt-20 items-center gap-12 px-6 py-20 lg:grid-cols-2">
          <div>
            <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">
              Member records
            </p>
            <h2 className="mt-3 font-display text-4xl font-semibold tracking-[-0.02em] text-foreground">
              Open a member. Understand the situation.
            </h2>
            <p className="mt-5 max-w-md text-base leading-relaxed text-muted">
              See a member’s Discord identity and recorded moderation history together. Staff can review past actions before deciding what to do next.
            </p>
            <p className="mt-4 max-w-md text-sm leading-relaxed text-muted-2">
              The interactive panel uses example members. Signed-in dashboards load the selected server’s real Discord members and moderation records.
            </p>
            <Link
              href="/commands"
              className={buttonVariants({ variant: 'subtle', size: 'md', className: 'mt-7 gap-2' })}
            >
              Browse bot commands
              <ArrowRight className="size-4" />
            </Link>
          </div>
          <CommandDemo />
        </div>
      </section>

      <section className="bg-surface">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <div className="max-w-2xl">
            <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">
              A complete moderation shift
            </p>
            <h2 className="mt-3 font-display text-4xl font-semibold tracking-[-0.02em] text-foreground">
              Review, act, and leave useful context.
            </h2>
          </div>
          <div className="mt-12 grid gap-px overflow-hidden rounded-lg border border-border bg-border md:grid-cols-3">
            {WORKFLOW.map((item) => {
              const Icon = item.icon
              return (
                <article key={item.title} className="bg-card p-7">
                  <Icon className="size-5 text-accent" />
                  <h3 className="mt-5 font-display text-lg font-semibold text-foreground">{item.title}</h3>
                  <p className="mt-2.5 text-sm leading-relaxed text-muted">{item.body}</p>
                </article>
              )
            })}
          </div>
        </div>
      </section>

      <Faq />

      <section className="border-t border-border">
        <div className="mx-auto max-w-4xl px-6 pb-24 pt-20 text-center">
          <h2 className="font-display text-4xl font-semibold tracking-[-0.02em] text-foreground sm:text-5xl">
            Ready to manage your server?
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-lg text-muted">
            Sign in with Discord, choose a server you administer, and open its moderation dashboard.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link
              href="/api/auth/discord/authorize"
              className={buttonVariants({ variant: 'primary', size: 'lg', className: 'gap-2.5 px-8' })}
            >
              <LogIn className="size-4.5" />
              Sign in with Discord
            </Link>
            <Link href="/commands" className={buttonVariants({ variant: 'outline', size: 'lg' })}>
              View commands
            </Link>
          </div>
        </div>
      </section>
    </>
  )
}
