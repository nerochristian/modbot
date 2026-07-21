import type { CSSProperties } from 'react'
import Link from 'next/link'
import {
  ArrowRight,
  FileText,
  LockKeyhole,
  Plus,
  Radar,
  Scale,
  ShieldCheck,
  TerminalSquare,
  Users,
} from 'lucide-react'
import { buttonVariants } from '@/components/ui/button'
import { Stamp } from '@/components/ui/stamp'
import { cn } from '@/lib/utils'

/**
 * The landing page as an open case file — "the records desk, in daylight."
 *
 * The storefront wears the product's own identity: porcelain paper, cobalt
 * ink, ruled lines, and the stamp/tick-meter signatures from the console.
 * Everything is paperwork: the hero is a filed case, features are an index
 * of services, the pitch is a paper trail. Server-rendered, no client JS.
 */

/* ---------------------------------------------------------------- */
/* Small print                                                      */

function Kicker({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-mono text-[0.6875rem] font-semibold tracking-[0.18em] text-muted-2 uppercase">
      <span className="text-accent">§</span> {children}
    </p>
  )
}

function SectionHead({
  kicker,
  title,
  lead,
}: {
  kicker: string
  title: string
  lead?: string
}) {
  return (
    <div className="max-w-2xl space-y-3">
      <Kicker>{kicker}</Kicker>
      <h2 className="font-display text-3xl tracking-tight text-balance sm:text-4xl">{title}</h2>
      {lead && <p className="text-base leading-7 text-muted">{lead}</p>}
    </div>
  )
}

/** Severity as the console renders it: a measured 5-tick gauge. */
function Ticks({ filled, tone, label }: { filled: number; tone: string; label: string }) {
  return (
    <span
      className="tickmeter"
      role="img"
      aria-label={label}
      style={{ '--tick-color': tone } as CSSProperties}
    >
      {Array.from({ length: 5 }, (_, i) => (
        <span key={i} className={cn('tick', i < filled && 'on')} />
      ))}
    </span>
  )
}

/** A redacted span of evidence — decoration, not content. */
function Redacted({ w }: { w: string }) {
  return (
    <span
      aria-hidden
      className={cn('inline-block h-3 translate-y-[2px] rounded-[3px] bg-foreground/75', w)}
    />
  )
}

/* ---------------------------------------------------------------- */
/* Hero exhibit — the case file itself                              */

function CaseFileSheet() {
  return (
    <div className="relative" aria-label="Example case file">
      <div className="sheet-under" aria-hidden />
      <div className="sheet p-5 sm:p-6">
        {/* File header */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-dashed pb-4">
          <Stamp id="CASE DKT-04821" at="2026-07-18T21:47:00Z" accent />
          <span className="font-mono text-[0.6875rem] tracking-[0.14em] text-muted-2 uppercase">
            Automod · Rule R-12
          </span>
        </div>

        {/* Record body */}
        <dl className="divide-y divide-border text-sm">
          {[
            {
              term: 'Subject',
              detail: (
                <span className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">@nitro_dealz</span>
                  <span className="mono-id text-xs text-muted-2">ID 883 401 772 094</span>
                </span>
              ),
            },
            {
              term: 'Trigger',
              detail: <span>Invite link · 4 channels in 11 seconds</span>,
            },
            {
              term: 'Severity',
              detail: (
                <span className="flex items-center gap-2.5">
                  <Ticks filled={4} tone="var(--sev-high)" label="Severity: high, 4 of 5" />
                  <span className="font-mono text-xs font-semibold text-sev-high uppercase">High</span>
                </span>
              ),
            },
            {
              term: 'Evidence',
              detail: (
                <span className="text-muted">
                  &ldquo;free nitro drop <Redacted w="w-24" /> claim <Redacted w="w-14" />&rdquo;
                  <span className="ml-2 font-mono text-[0.6875rem] text-muted-2 uppercase">4 msgs purged</span>
                </span>
              ),
            },
            {
              term: 'Action',
              detail: <span>Messages removed · 24&thinsp;h timeout</span>,
            },
            {
              term: 'Appeal',
              detail: <span>Window open until 07·25 · form delivered by DM</span>,
            },
          ].map((row) => (
            <div key={row.term} className="grid grid-cols-[5.5rem_1fr] gap-3 py-2.5">
              <dt className="font-mono text-[0.6875rem] leading-5 tracking-[0.14em] text-muted-2 uppercase">
                {row.term}
              </dt>
              <dd className="leading-5 text-foreground">{row.detail}</dd>
            </div>
          ))}
        </dl>

        {/* File footer: countersignature + the stamp moment */}
        <div className="flex items-end justify-between border-t border-dashed pt-4">
          <p className="font-mono text-[0.6875rem] leading-5 text-muted-2">
            on duty: <span className="text-muted">@kestrel</span>
            <br />
            time to file: <span className="text-muted">0.9s</span>
          </p>
          <span className="ink-stamp animate-stamp-in text-accent">Filed</span>
        </div>
      </div>
    </div>
  )
}

/* ---------------------------------------------------------------- */
/* Page                                                             */

const LEDGER = [
  { value: '12,438', label: 'servers on the desk' },
  { value: '1.28M', label: 'cases filed' },
  { value: '0.9s', label: 'catch to case, median' },
  { value: '96%', label: 'appeals decided in 48h' },
]

const STEPS = [
  {
    code: '01',
    title: 'Invite the bot',
    body: 'Authorize with Discord. Console access mirrors your live Administrator permission — there is no second role system to configure or forget.',
    note: 'about two minutes',
  },
  {
    code: '02',
    title: 'Set the rulebook',
    body: 'Switch on the automod rules you want — invites, spam bursts, slurs, raid patterns — with thresholds and exempt roles per rule.',
    note: 'sensible defaults included',
  },
  {
    code: '03',
    title: 'Work the caseload',
    body: 'Every catch arrives as a numbered case with evidence attached. Assign it, resolve it, or let the appeal run its course.',
    note: 'your whole team, one desk',
  },
]

const FEATURES = [
  {
    code: 'F-01',
    icon: ShieldCheck,
    name: 'Automod rulebook',
    body: 'Filters for invites, spam, slurs, and raids. Every trigger files a case with the evidence already attached — nothing enforced off the record.',
  },
  {
    code: 'F-02',
    icon: FileText,
    name: 'Case files',
    body: 'Warnings, timeouts, kicks, bans — numbered, searchable, and stamped with who acted, on what grounds, and when.',
  },
  {
    code: 'F-03',
    icon: Scale,
    name: 'Appeals desk',
    body: 'Members appeal through a tokenized form — it works even after a ban. Your team decides with the full record in view.',
  },
  {
    code: 'F-04',
    icon: Users,
    name: 'Member ledger',
    body: 'Standing, risk level, and full history per member. Know exactly who you are dealing with before you act.',
  },
  {
    code: 'F-05',
    icon: Radar,
    name: 'Desk analytics',
    body: 'Automod hit rates, enforcement trends, and moderator workload, charted week over week. See the desk, not just the queue.',
  },
  {
    code: 'F-06',
    icon: LockKeyhole,
    name: 'Team & roles',
    body: 'Admin, Moderator, Helper — a permission matrix your admins can edit, enforced on every page and every API call.',
  },
]

const TRAIL = [
  {
    time: '21:47:03Z',
    label: 'Rule R-12 trips',
    tone: 'var(--sev-high)',
    body: (
      <>
        <p className="text-sm leading-6 text-muted">
          &ldquo;free nitro drop <Redacted w="w-20" />&rdquo; — posted to 4 channels in 11 seconds.
          Messages purged on sight.
        </p>
        <p className="mt-2 font-mono text-[0.6875rem] tracking-[0.12em] text-muted-2 uppercase">
          Automod · evidence retained
        </p>
      </>
    ),
  },
  {
    time: '21:47:04Z',
    label: 'Case DKT-04821 filed',
    tone: 'var(--accent)',
    body: (
      <>
        <p className="text-sm leading-6 text-muted">
          Severity assessed high, 24&thinsp;h timeout applied, appeal window opened. The member
          gets a DM with the grounds and a form link.
        </p>
        <p className="mt-2 flex items-center gap-2.5">
          <Ticks filled={4} tone="var(--sev-high)" label="Severity: high, 4 of 5" />
          <span className="font-mono text-[0.6875rem] tracking-[0.12em] text-muted-2 uppercase">
            filed in 0.9s · no human woken up
          </span>
        </p>
      </>
    ),
  },
  {
    time: '07·19 09:12Z',
    label: 'Appeal decided',
    tone: 'var(--success)',
    body: (
      <>
        <p className="text-sm leading-6 text-muted">
          &ldquo;My account was compromised — I&rsquo;ve reset everything.&rdquo; A moderator reviews
          the statement next to the whole file and lifts the timeout.
        </p>
        <p className="mt-3">
          <span className="ink-stamp text-success" style={{ fontSize: '0.6875rem' }}>
            Approved
          </span>
        </p>
      </>
    ),
  },
]

const COMMANDS = [
  { cmd: '/warn @member <reason>', effect: 'files a case, DMs the grounds' },
  { cmd: '/timeout @member 24h', effect: 'enforces + records in one motion' },
  { cmd: '/case 4821', effect: 'pulls the full record into chat' },
  { cmd: '/history @member', effect: 'the ledger, without leaving Discord' },
]

const FAQ = [
  {
    q: 'Does Docket need Administrator?',
    a: 'The bot needs only the permissions it enforces with — manage messages, timeout, kick, ban. Console access is separate and mirrors your live Discord Administrator permission, checked on every request.',
  },
  {
    q: 'What happens to deleted message content?',
    a: 'Purged content is retained as case evidence, visible only to your moderation team, and can be erased per-case or server-wide at any time. Evidence never appears in public channels.',
  },
  {
    q: 'Can banned members actually appeal?',
    a: 'Yes. Appeal links are tokenized web forms, so they work for members who can no longer see the server. Decisions land back on the case file either way.',
  },
  {
    q: 'Does it replace my moderators?',
    a: 'No — it replaces their paperwork. Automod handles the obvious catches instantly; everything else becomes a clean, numbered case a human can decide in seconds instead of minutes.',
  },
  {
    q: 'What does it cost?',
    a: 'The desk is free for every server. Server Premium adds longer evidence retention, more automod rules, and priority support for communities that run a heavy caseload.',
  },
]

export default function LandingPage() {
  return (
    <div className="pb-24">
      {/* ============================================================ */}
      {/* § 01 — Intake                                                */}
      <section className="mx-auto grid max-w-6xl items-center gap-12 px-4 pt-16 pb-20 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16 lg:pt-24">
        <div className="space-y-7">
          <Kicker>01 · Form D-1 · Server intake</Kicker>
          <h1 className="font-display text-5xl leading-[1.02] tracking-tight text-balance sm:text-6xl lg:text-[4.25rem]">
            Moderation, <span className="text-accent">on the record.</span>
          </h1>
          <p className="max-w-xl text-lg leading-8 text-muted">
            Docket is the records desk for Discord servers. Automod that files real cases with
            evidence attached, appeals with due process, and a console your whole mod team works
            from — so every action can survive the question <em>&ldquo;why?&rdquo;</em>
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Link href="/register" className={buttonVariants({ size: 'lg' })}>
              Open the dashboard
              <ArrowRight className="size-4" />
            </Link>
            <Link href="/commands" className={buttonVariants({ variant: 'outline', size: 'lg' })}>
              Browse commands
            </Link>
          </div>
          <p className="font-mono text-xs tracking-[0.08em] text-muted-2">
            Free for every server · demo console preloaded · no card
          </p>
        </div>

        <CaseFileSheet />
      </section>

      {/* Ledger totals — one ruled line, not a wall of tiles. */}
      <section aria-label="Ledger totals" className="border-y bg-surface">
        <div className="mx-auto grid max-w-6xl grid-cols-2 divide-x divide-border lg:grid-cols-4">
          {LEDGER.map((item, i) => (
            <div key={item.label} className={cn('px-4 py-6 sm:px-6', i > 1 && 'border-t lg:border-t-0')}>
              <p className="mono-id text-2xl font-semibold tracking-tight sm:text-3xl">{item.value}</p>
              <p className="mt-1 font-mono text-[0.6875rem] tracking-[0.12em] text-muted-2 uppercase">
                {item.label}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ============================================================ */}
      {/* § 02 — Setup                                                 */}
      <section id="setup" className="scroll-mt-20">
        <div className="mx-auto max-w-6xl px-4 pt-20 sm:px-6">
          <SectionHead
            kicker="02 · Procedure"
            title="Open your desk in three motions"
            lead="No onboarding call, no config file. The desk is working before your coffee is."
          />
          <ol className="mt-10 grid gap-px overflow-hidden rounded-xl border bg-border sm:grid-cols-3">
            {STEPS.map((step) => (
              <li key={step.code} className="flex flex-col gap-3 bg-surface p-6">
                <span className="font-mono text-[0.6875rem] font-semibold tracking-[0.18em] text-accent uppercase">
                  Step {step.code}
                </span>
                <h3 className="font-display text-xl tracking-tight">{step.title}</h3>
                <p className="text-sm leading-6 text-muted">{step.body}</p>
                <p className="mt-auto border-t border-dashed pt-3 font-mono text-[0.6875rem] tracking-[0.1em] text-muted-2 uppercase">
                  {step.note}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ============================================================ */}
      {/* § 03 — Index of services                                     */}
      <section id="features" className="scroll-mt-20">
        <div className="mx-auto max-w-6xl px-4 pt-20 sm:px-6">
          <SectionHead
            kicker="03 · Index of services"
            title="Everything the desk handles"
            lead="Six surfaces, one continuous record. Each entry below is a page in the console, not a bullet point."
          />
          <div className="mt-10 grid overflow-hidden rounded-xl border md:grid-cols-2">
            {FEATURES.map((feature, i) => (
              <div
                key={feature.code}
                className={cn(
                  'group relative flex gap-4 p-6 transition-colors hover:bg-surface',
                  i > 0 && 'border-t',
                  i % 2 === 1 && 'md:border-l',
                  i === 1 && 'md:border-t-0',
                )}
              >
                {/* the docket rail wakes up on hover */}
                <span
                  aria-hidden
                  className="absolute inset-y-4 left-0 w-0.5 rounded-r bg-accent opacity-0 transition-opacity group-hover:opacity-100"
                />
                <feature.icon className="mt-0.5 size-5 shrink-0 text-accent" aria-hidden />
                <div className="space-y-1.5">
                  <div className="flex items-baseline gap-2.5">
                    <h3 className="font-display text-lg tracking-tight">{feature.name}</h3>
                    <span className="font-mono text-[0.625rem] font-medium tracking-[0.14em] text-muted-2 uppercase">
                      {feature.code}
                    </span>
                  </div>
                  <p className="text-sm leading-6 text-muted">{feature.body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============================================================ */}
      {/* § 04 — The record                                            */}
      <section className="mx-auto max-w-6xl px-4 pt-20 sm:px-6">
        <SectionHead
          kicker="04 · Chain of record"
          title="Every action leaves a paper trail"
          lead="From the second a rule trips to the moment an appeal is decided, it is one continuous file — so any moderator can pick up a case cold, and any decision can be defended later."
        />
        <ol className="relative mt-12 max-w-2xl space-y-10 border-l pl-8">
          {TRAIL.map((entry) => (
            <li key={entry.time} className="relative">
              <span
                aria-hidden
                className="absolute top-1 -left-[2.4rem] size-3 rounded-full border-2 border-paper"
                style={{ background: entry.tone }}
              />
              <p className="font-mono text-[0.6875rem] tracking-[0.14em] text-muted-2 uppercase">
                {entry.time}
              </p>
              <h3 className="mt-1 font-display text-lg tracking-tight">{entry.label}</h3>
              <div className="mt-2">{entry.body}</div>
            </li>
          ))}
        </ol>
      </section>

      {/* ============================================================ */}
      {/* § 05 — From chat                                             */}
      <section className="mx-auto max-w-6xl px-4 pt-20 sm:px-6">
        <div className="grid items-start gap-10 lg:grid-cols-[0.9fr_1.1fr]">
          <SectionHead
            kicker="05 · Field work"
            title="The desk answers from chat, too"
            lead="Moderators live in Discord, not in dashboards. Every filing the console can make, a slash command can make faster — and it lands on the same record."
          />
          <div className="overflow-hidden rounded-xl border">
            <div className="flex items-center gap-2 border-b bg-surface px-4 py-2.5">
              <TerminalSquare className="size-4 text-accent" aria-hidden />
              <span className="font-mono text-[0.6875rem] tracking-[0.14em] text-muted-2 uppercase">
                Slash commands · excerpt
              </span>
            </div>
            <ul className="divide-y">
              {COMMANDS.map((row) => (
                <li
                  key={row.cmd}
                  className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 px-4 py-3.5 transition-colors hover:bg-surface"
                >
                  <code className="mono-id text-sm font-medium text-accent">{row.cmd}</code>
                  <span className="text-sm text-muted">{row.effect}</span>
                </li>
              ))}
            </ul>
            <div className="border-t bg-surface px-4 py-3">
              <Link
                href="/commands"
                className="focus-ring inline-flex items-center gap-1.5 rounded-md text-sm font-medium text-accent hover:underline"
              >
                Browse the full command directory
                <ArrowRight className="size-3.5" aria-hidden />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ============================================================ */}
      {/* § 06 — Questions                                             */}
      <section className="mx-auto max-w-6xl px-4 pt-20 sm:px-6">
        <SectionHead kicker="06 · For the record" title="Questions, answered" />
        <div className="mt-8 max-w-3xl divide-y border-y">
          {FAQ.map((item) => (
            <details key={item.q} className="group">
              <summary className="focus-ring flex cursor-pointer list-none items-center justify-between gap-4 rounded-md py-4 text-left [&::-webkit-details-marker]:hidden">
                <span className="font-medium">{item.q}</span>
                <Plus
                  className="size-4 shrink-0 text-muted-2 transition-transform group-open:rotate-45"
                  aria-hidden
                />
              </summary>
              <p className="pb-5 text-sm leading-7 text-muted">{item.a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* ============================================================ */}
      {/* Closing stamp                                                */}
      <section className="mx-auto max-w-6xl px-4 pt-20 sm:px-6">
        <div className="sheet ruled overflow-hidden px-6 py-14 text-center sm:py-16">
          <Kicker>07 · Disposition</Kicker>
          <h2 className="mx-auto mt-3 max-w-xl font-display text-4xl tracking-tight text-balance sm:text-5xl">
            Put your server on the record.
          </h2>
          <p className="mx-auto mt-4 max-w-md text-base leading-7 text-muted">
            The next incident is going to happen either way. The only question is whether
            there&rsquo;s a file.
          </p>
          <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
            <Link href="/register" className={buttonVariants({ size: 'lg' })}>
              Open the dashboard
              <ArrowRight className="size-4" />
            </Link>
            <Link href="/login" className={buttonVariants({ variant: 'outline', size: 'lg' })}>
              Sign in
            </Link>
          </div>
          <p className="mt-6 font-mono text-xs tracking-[0.08em] text-muted-2">
            setup takes about two minutes · free forever for small desks
          </p>
        </div>
      </section>
    </div>
  )
}
