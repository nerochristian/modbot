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
 * The landing page as a records-office print poster.
 *
 * Same paperwork soul as the console — stamps, tick-meters, ruled ledgers —
 * but set like a brutalist broadsheet: enormous stacked type, ghost section
 * numerals, a stamp that slams onto the headline, a ticker of live filings,
 * and ledger rows that invert to solid cobalt. Drama from scale and ink,
 * never glow. Server-rendered, no client JS.
 */

/* ---------------------------------------------------------------- */
/* Small print                                                      */

function Kicker({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-mono text-[0.6875rem] font-semibold tracking-[0.22em] text-muted-2 uppercase">
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
    <div className="relative z-10 max-w-2xl space-y-4">
      <Kicker>{kicker}</Kicker>
      <h2 className="font-display text-4xl leading-[0.95] tracking-tight text-balance uppercase sm:text-5xl">
        {title}
      </h2>
      {lead && <p className="text-base leading-7 text-muted">{lead}</p>}
    </div>
  )
}

/** Poster folio — the huge outlined numeral behind each section. */
function Ghost({ n, className }: { n: string; className?: string }) {
  return (
    <span
      aria-hidden
      className={cn('ghost-numeral text-[9rem] sm:text-[14rem]', className)}
    >
      {n}
    </span>
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
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-dashed pb-4">
          <Stamp id="CASE DKT-04821" at="2026-07-18T21:47:00Z" accent />
          <span className="font-mono text-[0.6875rem] tracking-[0.14em] text-muted-2 uppercase">
            Automod · Rule R-12
          </span>
        </div>

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
/* Copy                                                             */

const TICKER = [
  { text: 'DKT-04821 FILED · R-12 INVITES', tone: 'var(--accent)' },
  { text: 'AP-0912 APPROVED · TIMEOUT LIFTED', tone: 'var(--success)' },
  { text: 'R-07 TRIPPED · SPAM BURST · 6 MSGS PURGED', tone: 'var(--danger)' },
  { text: 'DKT-04822 FILED · MANUAL WARN', tone: 'var(--accent)' },
  { text: 'DKT-04818 RESOLVED · NO FURTHER ACTION', tone: 'var(--success)' },
  { text: 'R-12 TRIPPED · INVITE LINK · 24H TIMEOUT', tone: 'var(--danger)' },
  { text: 'AP-0913 DENIED · RECORD STANDS', tone: 'var(--accent)' },
  { text: 'DKT-04825 FILED · RAID PATTERN · 14 ACCOUNTS', tone: 'var(--danger)' },
]

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
    icon: ShieldCheck,
    name: 'Automod rulebook',
    body: 'Filters for invites, spam, slurs, and raids. Every trigger files a case with the evidence already attached — nothing enforced off the record.',
  },
  {
    icon: FileText,
    name: 'Case files',
    body: 'Warnings, timeouts, kicks, bans — numbered, searchable, and stamped with who acted, on what grounds, and when.',
  },
  {
    icon: Scale,
    name: 'Appeals desk',
    body: 'Members appeal through a tokenized form — it works even after a ban. Your team decides with the full record in view.',
  },
  {
    icon: Users,
    name: 'Member ledger',
    body: 'Standing, risk level, and full history per member. Know exactly who you are dealing with before you act.',
  },
  {
    icon: Radar,
    name: 'Desk analytics',
    body: 'Automod hit rates, enforcement trends, and moderator workload, charted week over week. See the desk, not just the queue.',
  },
  {
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

/* ---------------------------------------------------------------- */
/* Page                                                             */

export default function LandingPage() {
  return (
    <div className="overflow-x-clip pb-24">
      {/* ============================================================ */}
      {/* § 01 — The poster                                            */}
      <section className="relative mx-auto max-w-6xl px-4 pt-14 sm:px-6 lg:pt-20">
        <Ghost n="01" className="-top-6 right-0 hidden lg:block" />
        <div className="relative z-10 grid items-center gap-14 lg:grid-cols-[1.1fr_0.9fr] lg:gap-12">
          <div className="space-y-8">
            <Kicker>01 · Form D-1 · Server intake</Kicker>
            <h1 className="relative font-display leading-[0.88] font-bold tracking-tight uppercase">
              <span className="block text-[clamp(3.25rem,9vw,7rem)]">Every ban,</span>
              <span className="block text-[clamp(3.25rem,9vw,7rem)]">every warn,</span>
              <span className="block text-[clamp(3.25rem,9vw,7rem)] text-accent">
                on record.
              </span>
              {/* the clerk's verdict, slammed over the headline */}
              <span
                aria-hidden
                className="ink-stamp stamp-slam absolute -top-3 right-0 border-[3.5px] text-2xl text-danger sm:text-3xl lg:-right-6"
              >
                Filed
              </span>
            </h1>
            <p className="max-w-xl text-lg leading-8 text-muted">
              Docket is the records desk for Discord servers. Automod that files real cases with
              evidence attached, appeals with due process, and a console your whole mod team works
              from — so every action survives the question <em>&ldquo;why?&rdquo;</em>
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
        </div>
      </section>

      {/* The wire — filings running across the page. */}
      <div className="mt-16 overflow-hidden border-y bg-surface py-3" aria-hidden>
        <div className="marquee-track">
          {[0, 1].map((copy) => (
            <div key={copy} className="flex shrink-0">
              {TICKER.map((item) => (
                <span
                  key={`${copy}-${item.text}`}
                  className="mx-6 flex items-center gap-2.5 font-mono text-[0.6875rem] font-medium tracking-[0.14em] whitespace-nowrap text-muted uppercase"
                >
                  <span
                    className="size-1.5 rounded-full"
                    style={{ background: item.tone }}
                  />
                  {item.text}
                </span>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Ledger totals — numerals big enough to audit from across the room. */}
      <section aria-label="Ledger totals" className="border-b bg-surface">
        <div className="mx-auto grid max-w-6xl grid-cols-2 divide-x divide-border lg:grid-cols-4">
          {LEDGER.map((item, i) => (
            <div key={item.label} className={cn('px-4 py-8 sm:px-6', i > 1 && 'border-t lg:border-t-0')}>
              <p className="mono-id text-4xl font-semibold tracking-tight sm:text-5xl">{item.value}</p>
              <p className="mt-2 font-mono text-[0.6875rem] tracking-[0.14em] text-muted-2 uppercase">
                {item.label}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ============================================================ */}
      {/* § 02 — Setup                                                 */}
      <section id="setup" className="scroll-mt-20">
        <div className="relative mx-auto max-w-6xl px-4 pt-24 sm:px-6">
          <Ghost n="02" className="-top-2 right-0" />
          <SectionHead
            kicker="02 · Procedure"
            title="Open your desk in three motions"
            lead="No onboarding call, no config file. The desk is working before your coffee is."
          />
          <ol className="relative z-10 mt-12 grid gap-px overflow-hidden rounded-xl border bg-border sm:grid-cols-3">
            {STEPS.map((step) => (
              <li key={step.code} className="flex flex-col gap-4 bg-surface p-7">
                <span className="font-display text-5xl font-bold text-accent">{step.code}</span>
                <h3 className="font-display text-2xl tracking-tight">{step.title}</h3>
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
        <div className="relative mx-auto max-w-6xl px-4 pt-24 sm:px-6">
          <Ghost n="03" className="-top-2 right-0" />
          <SectionHead
            kicker="03 · Index of services"
            title="Everything the desk handles"
            lead="Six surfaces, one continuous record. Each entry below is a page in the console, not a bullet point."
          />
          <ol className="relative z-10 mt-12 border-t">
            {FEATURES.map((feature, i) => (
              <li
                key={feature.name}
                className="group grid items-baseline gap-x-8 gap-y-2 border-b px-4 py-7 transition-colors duration-150 hover:bg-accent sm:px-6 md:grid-cols-[4.5rem_1.1fr_1.3fr]"
              >
                <span className="font-display text-3xl font-bold text-muted-2 transition-colors group-hover:text-accent-foreground/60 sm:text-4xl">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <h3 className="flex items-center gap-3 font-display text-2xl tracking-tight transition-colors group-hover:text-accent-foreground sm:text-3xl">
                  <feature.icon
                    className="size-6 shrink-0 text-accent transition-colors group-hover:text-accent-foreground"
                    aria-hidden
                  />
                  {feature.name}
                </h3>
                <p className="text-sm leading-6 text-muted transition-colors group-hover:text-accent-foreground/85">
                  {feature.body}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ============================================================ */}
      {/* § 04 — The record                                            */}
      <section className="relative mx-auto max-w-6xl px-4 pt-24 sm:px-6">
        <Ghost n="04" className="-top-2 right-0" />
        <SectionHead
          kicker="04 · Chain of record"
          title="Every action leaves a paper trail"
          lead="From the second a rule trips to the moment an appeal is decided, it is one continuous file — so any moderator can pick up a case cold, and any decision can be defended later."
        />
        <ol className="relative z-10 mt-14 max-w-2xl space-y-12 border-l-2 pl-8">
          {TRAIL.map((entry) => (
            <li key={entry.time} className="relative">
              <span
                aria-hidden
                className="absolute top-1.5 -left-[2.47rem] size-3.5 rounded-full border-2 border-paper"
                style={{ background: entry.tone }}
              />
              <p className="font-mono text-[0.6875rem] tracking-[0.16em] text-muted-2 uppercase">
                {entry.time}
              </p>
              <h3 className="mt-1.5 font-display text-2xl tracking-tight">{entry.label}</h3>
              <div className="mt-2.5">{entry.body}</div>
            </li>
          ))}
        </ol>
      </section>

      {/* ============================================================ */}
      {/* § 05 — From chat                                             */}
      <section className="relative mx-auto max-w-6xl px-4 pt-24 sm:px-6">
        <Ghost n="05" className="-top-2 right-0" />
        <div className="relative z-10 grid items-start gap-10 lg:grid-cols-[0.9fr_1.1fr]">
          <SectionHead
            kicker="05 · Field work"
            title="The desk answers from chat, too"
            lead="Moderators live in Discord, not in dashboards. Every filing the console can make, a slash command can make faster — and it lands on the same record."
          />
          <div className="overflow-hidden rounded-xl border">
            <div className="flex items-center gap-2 bg-foreground px-4 py-3 text-paper">
              <TerminalSquare className="size-4" aria-hidden />
              <span className="font-mono text-[0.6875rem] tracking-[0.16em] uppercase opacity-80">
                Slash commands · excerpt
              </span>
            </div>
            <ul className="divide-y">
              {COMMANDS.map((row) => (
                <li
                  key={row.cmd}
                  className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 px-4 py-4 transition-colors hover:bg-surface"
                >
                  <code className="mono-id text-sm font-semibold text-accent">{row.cmd}</code>
                  <span className="text-sm text-muted">{row.effect}</span>
                </li>
              ))}
            </ul>
            <div className="border-t bg-surface px-4 py-3.5">
              <Link
                href="/commands"
                className="focus-ring inline-flex items-center gap-1.5 rounded-md text-sm font-semibold text-accent hover:underline"
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
      <section className="relative mx-auto max-w-6xl px-4 pt-24 sm:px-6">
        <Ghost n="06" className="-top-2 right-0" />
        <SectionHead kicker="06 · For the record" title="Questions, answered" />
        <div className="relative z-10 mt-10 max-w-3xl divide-y border-y">
          {FAQ.map((item) => (
            <details key={item.q} className="group">
              <summary className="focus-ring flex cursor-pointer list-none items-center justify-between gap-4 rounded-md py-5 text-left font-display text-lg tracking-tight [&::-webkit-details-marker]:hidden">
                {item.q}
                <Plus
                  className="size-5 shrink-0 text-muted-2 transition-transform group-open:rotate-45"
                  aria-hidden
                />
              </summary>
              <p className="pb-6 text-sm leading-7 text-muted">{item.a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* ============================================================ */}
      {/* § 07 — The ink slab                                          */}
      <section className="mx-auto max-w-6xl px-4 pt-24 sm:px-6">
        <div className="relative overflow-hidden rounded-2xl bg-foreground px-6 py-20 text-center text-paper sm:py-24">
          {/* oversized clerk's mark bleeding off the slab */}
          <span
            aria-hidden
            className="ink-stamp absolute -top-4 -right-10 rotate-[8deg] border-4 text-5xl opacity-[0.08] sm:text-7xl"
          >
            Approved
          </span>
          <span
            aria-hidden
            className="ink-stamp absolute -bottom-8 -left-8 border-4 text-5xl opacity-[0.08] sm:text-7xl"
          >
            On record
          </span>
          <p className="font-mono text-[0.6875rem] font-semibold tracking-[0.22em] uppercase opacity-70">
            § 07 · Disposition
          </p>
          <h2 className="mx-auto mt-4 max-w-3xl font-display text-[clamp(2.5rem,6vw,4.75rem)] leading-[0.92] font-bold tracking-tight text-balance uppercase">
            Put your server on the record.
          </h2>
          <p className="mx-auto mt-5 max-w-md text-base leading-7 opacity-75">
            The next incident is going to happen either way. The only question is whether
            there&rsquo;s a file.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link href="/register" className={buttonVariants({ size: 'lg' })}>
              Open the dashboard
              <ArrowRight className="size-4" />
            </Link>
            <Link
              href="/login"
              className={cn(
                buttonVariants({ variant: 'outline', size: 'lg' }),
                'border-paper/30 text-paper hover:bg-paper/10',
              )}
            >
              Sign in
            </Link>
          </div>
          <p className="mt-7 font-mono text-xs tracking-[0.08em] opacity-60">
            setup takes about two minutes · free forever for small desks
          </p>
        </div>
      </section>
    </div>
  )
}
