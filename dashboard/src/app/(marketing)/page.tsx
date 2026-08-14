import Link from 'next/link'
import {
  ArrowRight,
  FileClock,
  LogIn,
  MessageSquareWarning,
  Moon,
  Settings2,
  ShieldCheck,
  TicketCheck,
  UsersRound,
  Zap,
} from 'lucide-react'
import { buttonVariants } from '@/components/ui/button'
import { LiveWire } from '@/components/marketing/live-wire'
import { CircuitField } from '@/components/marketing/circuit-field'
import { CommandDemo } from '@/components/marketing/command-demo'
import { Faq } from '@/components/marketing/faq'

/**
 * Landing — "A quiet shift."
 *
 * The page is structured as one real moderation sequence so visitors feel
 * what Docket does before they read a spec: the quiet watch (midnight), the
 * raid that gets absorbed (Live Wire), and the calm morning ledger the staff
 * actually wakes up to. The signature is the threat-exposure bar hugging the
 * Live Wire card — it swells as the counter climbs and flattens once the
 * board settles into "Contained".
 */

const AREAS = [
  { value: 'Automod', note: 'Watches while you sleep' },
  { value: 'Cases', note: 'Nothing lost between shifts' },
  { value: 'Reports', note: 'Members flag it privately' },
  { value: 'Tickets', note: 'Support stays in channels' },
]

const CAPABILITIES = [
  {
    icon: ShieldCheck,
    title: 'Automod does the first read',
    body: 'Spam, links, invites, floods, caps, blocked words, duplicate spam, raid behaviour — each rule has its own response, so the bot only steps in where it should.',
  },
  {
    icon: FileClock,
    title: 'Cases keep the second pair of eyes',
    body: 'Warns, timeouts, kicks and bans carry the reason, the evidence and the staff note. The next moderator starts with context, not a question in mod chat.',
  },
  {
    icon: MessageSquareWarning,
    title: 'Reports reach staff without the theatre',
    body: 'Any member can use /report. It lands in the moderation queue with the reporter hidden, so people actually use it instead of posting screenshots.',
  },
  {
    icon: TicketCheck,
    title: 'Tickets fit the way your server already works',
    body: 'Choose categories, questions, optional emoji, staff access, private channels and transcript logging — without touching a config file.',
  },
]

const SETUP = [
  {
    n: '01',
    title: 'Sign in with Discord',
    body: 'We only read what Discord already knows. Your password never leaves Discord’s side of the page.',
  },
  {
    n: '02',
    title: 'Pick a server you administer',
    body: 'The dashboard only lists servers where your live Discord permission is Administrator — nothing else shows up.',
  },
  {
    n: '03',
    title: 'Set the shift up once',
    body: 'Flip the modules on, choose the log channel, build two or three automod rules. After that it mostly runs itself.',
  },
]

const HANDOVER = [
  { icon: UsersRound, title: 'See who you’re dealing with', body: 'Identity, roles, recorded actions, open cases, appeals and staff notes on one screen.' },
  { icon: Settings2, title: 'Take the action that fits', body: 'Warn, timeout, kick, ban or note — with the reason stamped onto the record, not typed twice.' },
  { icon: FileClock, title: 'Leave a ledger the next mod can trust', body: 'Cases, action logs, reports and transcripts give the morning shift enough context to continue without a recap.' },
]

export default function LandingPage() {
  return (
    <>
      {/* ————— Hero — "the watch" ————— */}
      <section className="relative overflow-hidden border-b border-border">
        <CircuitField className="pointer-events-none absolute inset-0 h-full w-full opacity-60" />
        <div className="scanfield pointer-events-none absolute inset-0 opacity-30" />
        {/* ambient corners */}
        <div
          className="pointer-events-none absolute -left-32 top-0 h-[420px] w-[420px] rounded-full opacity-20 blur-[120px]"
          style={{ background: 'radial-gradient(circle, var(--brand-from), transparent 70%)' }}
        />
        <div
          className="pointer-events-none absolute -right-24 bottom-0 h-[380px] w-[380px] rounded-full opacity-18 blur-[120px]"
          style={{ background: 'radial-gradient(circle, var(--brand-cyan), transparent 70%)' }}
        />
        {/* central candle-line to keep a datum in the hero */}
        <div className="pointer-events-none absolute left-1/2 top-0 hidden h-full w-px bg-border lg:block" />

        <div className="relative mx-auto grid max-w-6xl items-center gap-x-12 gap-y-10 px-6 py-14 lg:grid-cols-[0.92fr_1.08fr] lg:py-16">
          <div>
            <p className="inline-flex items-center gap-2 rounded-sm border border-border bg-surface px-3 py-1 font-mono text-[0.6875rem] font-medium uppercase tracking-[0.16em] text-accent">
              <span className="inline-flex size-1.5 rounded-full bg-accent wire-blip" />
              Moderation, uneventful
            </p>
            <h1 className="mt-6 font-display text-[3.25rem] font-semibold leading-[0.96] tracking-[-0.03em] text-foreground sm:text-[3.9rem]">
              The raid happens.
              <br />
              <span className="text-brand-gradient">Your server stays calm.</span>
            </h1>
            <p className="mt-6 max-w-lg text-lg leading-relaxed text-muted">
              Docket is the calm layer on top of your Discord server — automod that absorbs the noise,
              a case ledger that remembers every action, and tickets &amp; reports that stay where your team can read them.
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
                href="#the-quiet-shift"
                className={buttonVariants({ variant: 'outline', size: 'lg', className: 'gap-2' })}
              >
                See a quiet shift
                <ArrowRight className="size-4" />
              </Link>
            </div>
            <p className="mt-5 font-mono text-[0.6875rem] uppercase tracking-[0.14em] text-muted-2">
              Access requires live Administrator permission on the server
            </p>
          </div>

          {/* Live Wire framed by its exposure bar */}
          <div className="lg:-mr-4">
            <div className="mb-3 flex items-center justify-between font-mono text-[0.625rem] uppercase tracking-[0.14em] text-muted-2">
              <span>Ambient exposure</span>
              <span className="text-threat">Monitoring · example</span>
            </div>

            <div className="relative">
              <LiveWire />
            </div>

            {/* signature: the threat bar that swells as the raid lands, then flattens */}
            <div className="mt-4">
              <div className="h-1 overflow-hidden rounded-full bg-surface-2">
                <div className="swell h-full w-full rounded-full" />
              </div>
              <div className="mt-2 flex items-center justify-between font-mono text-[0.625rem] uppercase tracking-[0.14em] text-muted-2">
                <span>0 events/min</span>
                <span>Swells as the raid lands — flattening as it’s contained</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ————— Sticky strip — qualitative, not a template grid ————— */}
      <section className="border-b border-border bg-surface">
        <div className="mx-auto grid max-w-6xl grid-cols-2 gap-px overflow-hidden sm:grid-cols-4">
          {AREAS.map((area) => (
            <div key={area.value} className="group px-6 py-6">
              <div className="font-display text-xl font-semibold tracking-tight text-foreground">
                {area.value}
              </div>
              <div className="mt-1 text-sm leading-snug text-muted">{area.note}</div>
              <div className="mt-3 h-px w-6 bg-border transition-all group-hover:w-10 group-hover:bg-accent" />
            </div>
          ))}
        </div>
      </section>

      {/* ————— The quiet shift — a timeline, not feature cards ————— */}
      <section id="the-quiet-shift" className="mx-auto max-w-6xl scroll-mt-20 px-6 py-20">
        <div className="max-w-2xl">
          <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">
            One real shift
          </p>
          <h2 className="mt-3 font-display text-4xl font-semibold tracking-[-0.02em] text-foreground">
            What happens between midnight and morning.
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted">
            The pattern is always the same: the bot does the visible work at 2 a.m., the ledger does the
            remembering, and the morning moderator starts with facts, not a search through deleted messages.
          </p>
        </div>

        <div className="mt-14 grid gap-px overflow-hidden rounded-lg border border-border bg-border lg:grid-cols-3">
          {/* Midnight */}
          <div className="shift-step is-active relative bg-surface p-7">
            <div className="flex items-center gap-3">
              <span className="shift-dot grid size-8 place-items-center rounded-full border-2 border-accent bg-card">
                <Moon className="size-4 text-accent" />
              </span>
              <div>
                <p className="font-mono text-[0.625rem] uppercase tracking-[0.14em] text-muted-2">00:00–04:00</p>
                <h3 className="font-display text-lg font-semibold text-foreground">The bot is awake</h3>
              </div>
            </div>
            <ul className="mt-5 space-y-3 text-sm leading-relaxed text-muted">
              <li>Every new message scanned against your rules before a human ever sees it.</li>
              <li>First-time accounts get looked at twice; old members get the benefit of the doubt.</li>
              <li>Everything suspicious is filed instantly, not screenshotted into mod chat.</li>
            </ul>
          </div>

          {/* The raid */}
          <div className="shift-step is-active relative bg-card p-7">
            <div className="flex items-center gap-3">
              <span className="shift-dot grid size-8 place-items-center rounded-full border-2 border-accent bg-card">
                <Zap className="size-4 text-accent" />
              </span>
              <div>
                <p className="font-mono text-[0.625rem] uppercase tracking-[0.14em] text-muted-2">02:17</p>
                <h3 className="font-display text-lg font-semibold text-foreground">The raid lands</h3>
              </div>
            </div>
            <ul className="mt-5 space-y-3 text-sm leading-relaxed text-muted">
              <li>Three hundred spoofed accounts stream into #general at once.</li>
              <li>Each message is stamped <span className="text-threat font-medium">BLOCKED</span> the moment it matches a rule.</li>
              <li>The channel never fills up — the swelled exposure bar snaps back to zero in the same minute.</li>
            </ul>
          </div>

          {/* Morning handover */}
          <div className="shift-step is-active relative bg-surface p-7">
            <div className="flex items-center gap-3">
              <span className="shift-dot grid size-8 place-items-center rounded-full border-2 border-accent bg-card">
                <FileClock className="size-4 text-accent" />
              </span>
              <div>
                <p className="font-mono text-[0.625rem] uppercase tracking-[0.14em] text-muted-2">08:30</p>
                <h3 className="font-display text-lg font-semibold text-foreground">Morning handover</h3>
              </div>
            </div>
            <ul className="mt-5 space-y-3 text-sm leading-relaxed text-muted">
              <li>The shift opens with one case ledger, not a pile of pings.</li>
              <li>Every action from the raid already has a case ID, a reason and a timestamp.</li>
              <li>The next moderator continues; nobody asks “what happened last night”.</li>
            </ul>
          </div>
        </div>
      </section>

      {/* ————— Capabilities — kept quiet so the timeline carries the drama ————— */}
      <section id="features" className="border-y border-border bg-surface">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <div className="max-w-2xl">
            <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">
              What Docket actually does
            </p>
            <h2 className="mt-3 font-display text-4xl font-semibold tracking-[-0.02em] text-foreground">
              The four things your team uses every day.
            </h2>
          </div>

          <div className="mt-12 grid gap-px overflow-hidden rounded-lg border border-border bg-border md:grid-cols-2">
            {CAPABILITIES.map((feature) => {
              const Icon = feature.icon
              return (
                <article key={feature.title} className="bg-surface p-7 sm:p-8">
                  <span className="grid size-10 place-items-center rounded-md border border-accent-line bg-accent-soft text-accent">
                    <Icon className="size-5" />
                  </span>
                  <h3 className="mt-5 font-display text-xl font-semibold tracking-tight text-foreground">
                    {feature.title}
                  </h3>
                  <p className="mt-2.5 text-sm leading-relaxed text-muted">{feature.body}</p>
                </article>
              )
            })}
          </div>
        </div>
      </section>

      {/* ————— Setup (3 steps, genuinely a sequence) ————— */}
      <section id="setup" className="mx-auto max-w-6xl scroll-mt-20 px-6 py-20">
        <div className="max-w-2xl">
          <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">
            Getting set up
          </p>
          <h2 className="mt-3 font-display text-4xl font-semibold tracking-[-0.02em] text-foreground">
            From Discord to your dashboard in three moves.
          </h2>
        </div>

        <div className="mt-12 grid gap-px overflow-hidden rounded-lg border border-border bg-border md:grid-cols-3">
          {SETUP.map((step) => (
            <article key={step.n} className="bg-card p-7">
              <span className="font-mono text-sm font-semibold text-accent">{step.n}</span>
              <h3 className="mt-4 font-display text-xl font-semibold tracking-tight text-foreground">{step.title}</h3>
              <p className="mt-2.5 text-sm leading-relaxed text-muted">{step.body}</p>
            </article>
          ))}
        </div>
      </section>

      {/* ————— Member records — the payoff demo ————— */}
      <section id="members" className="border-y border-border bg-surface">
        <div className="mx-auto grid max-w-6xl scroll-mt-20 items-center gap-12 px-6 py-20 lg:grid-cols-2">
          <div>
            <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">
              Member records
            </p>
            <h2 className="mt-3 font-display text-4xl font-semibold tracking-[-0.02em] text-foreground">
              Open a member. Know what kind of situation you’re in.
            </h2>
            <p className="mt-5 max-w-md text-base leading-relaxed text-muted">
              Docket shows their Discord identity next to the recorded history — every past warning, timeout,
              ban, appeal and staff note attached to one person, not scattered across three bots.
            </p>
            <p className="mt-4 max-w-md text-sm leading-relaxed text-muted-2">
              The interactive panel on this page uses example members. Once you sign in, the same panels load the
              selected server’s real Discord members and moderation records.
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

      {/* ————— Handover discipline ————— */}
      <section className="bg-paper">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <div className="max-w-2xl">
            <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">
              Between shifts
            </p>
            <h2 className="mt-3 font-display text-4xl font-semibold tracking-[-0.02em] text-foreground">
              Review, act, and leave something the next moderator can use.
            </h2>
          </div>
          <div className="mt-12 grid gap-px overflow-hidden rounded-lg border border-border bg-border md:grid-cols-3">
            {HANDOVER.map((item) => {
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

      {/* ————— Final CTA ————— */}
      <section className="border-t border-border">
        <div className="mx-auto max-w-4xl px-6 pb-24 pt-20 text-center">
          <h2 className="font-display text-4xl font-semibold tracking-[-0.02em] text-foreground sm:text-5xl">
            Ready for a quieter night?
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-lg text-muted">
            Sign in with Discord, pick the server you administer, and open the moderation dashboard —
            the raid keeps happening; you just stop hearing about it.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link
              href="/api/auth/discord/authorize"
              className={buttonVariants({ variant: 'primary', size: 'lg', className: 'gap-2.5 px-8' })}
            >
              <LogIn className="size-4" />
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
