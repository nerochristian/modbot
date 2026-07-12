import Link from 'next/link'
import { ArrowRight, LogIn } from 'lucide-react'
import { buttonVariants } from '@/components/ui/button'
import { LiveWire } from '@/components/marketing/live-wire'
import { Pricing } from '@/components/marketing/pricing'
import { Faq } from '@/components/marketing/faq'

// The three things a shift actually does, in order. Numbered because it IS a
// sequence: a threat arrives, it's judged, it becomes a permanent record.
const PIPELINE = [
  {
    n: '01',
    head: 'It arrives',
    body: 'Raids, spam floods, scam links, mention storms. Docket watches every message the instant it posts — before a human is even online.',
  },
  {
    n: '02',
    head: 'It’s judged',
    body: 'Layered rules score content in real time and act: block, mute, timeout, ban. Severity decides the response. No queue, no delay.',
  },
  {
    n: '03',
    head: 'It’s on the record',
    body: 'Every action opens a case with evidence, reason, and the moderator or rule behind it. Nothing is lost between shifts.',
  },
]

const STATS = [
  { value: '2.5M+', label: 'Messages scanned daily' },
  { value: '40k+', label: 'Communities protected' },
  { value: '180ms', label: 'Median action time' },
  { value: '99.99%', label: 'Uptime' },
]

// One real case file, shown in full — not six feature cards.
const CASE = {
  ref: 'CASE-0421',
  filed: '07·12 14:22Z',
  subject: 'user4821',
  type: 'Ban',
  severity: 'critical',
  reason: 'Coordinated raid — 1 of 300 spoofed accounts posting scam links to @everyone within a 9-second window.',
  rule: 'raid-shield · mention-flood',
  evidence: '@everyone free nitro → grabnitro.gg',
}

const TESTIMONIALS = [
  { quote: 'Docket caught a 300-account raid before a single message landed in general. We woke up to a clean log instead of a cleanup.', name: 'Sarah Chen', title: 'Head Moderator, The Nexus' },
  { quote: 'The case system replaced a spreadsheet and three bots. Every mod sees the full history the moment they open a member.', name: 'Marcus Reid', title: 'Server Owner, Forge & Anvil' },
  { quote: 'Appeals finally feel fair. The queue keeps every decision consistent, and members can see we actually reviewed them.', name: 'Priya Nair', title: 'Community Manager, Vela' },
]

export default function LandingPage() {
  return (
    <>
      {/* ============================================================ */}
      {/* ACT I — the incident. The hero IS the product, mid-raid.     */}
      {/* ============================================================ */}
      <section className="relative overflow-hidden border-b border-border">
        <div className="pointer-events-none absolute inset-0 scanfield opacity-60" />
        {/* A faint vertical rule anchors the asymmetric split. */}
        <div className="pointer-events-none absolute left-1/2 top-0 hidden h-full w-px bg-border lg:block" />
        <div className="mx-auto grid max-w-6xl items-center gap-x-12 gap-y-10 px-6 py-16 lg:grid-cols-[0.85fr_1.15fr] lg:py-20">
          {/* Left — the claim */}
          <div>
            <p className="inline-flex items-center gap-2 rounded-sm border border-border bg-surface px-3 py-1 font-mono text-[0.6875rem] font-medium uppercase tracking-[0.16em] text-accent">
              <span className="inline-flex size-1.5 rounded-full bg-threat wire-blip" />
              Raid in progress
            </p>
            <h1 className="mt-6 font-display text-[2.75rem] font-semibold leading-[0.95] tracking-[-0.03em] text-foreground sm:text-6xl">
              300 accounts
              <br />
              hit your server.
              <br />
              <span className="text-accent">Nobody saw&nbsp;it.</span>
            </h1>
            <p className="mt-6 max-w-md text-lg leading-relaxed text-muted">
              Docket reads every message the instant it posts and stops raids, spam, and scams
              before your community notices. Each action becomes a case you can read back.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link
                href="/api/auth/discord/authorize"
                className={buttonVariants({ variant: 'primary', size: 'lg', className: 'gap-2.5 px-7' })}
              >
                <LogIn className="size-4" />
                Deploy Docket
              </Link>
              <Link
                href="#pipeline"
                className={buttonVariants({ variant: 'outline', size: 'lg', className: 'gap-2' })}
              >
                How it works
                <ArrowRight className="size-4" />
              </Link>
            </div>
            <p className="mt-5 font-mono text-[0.6875rem] uppercase tracking-[0.14em] text-muted-2">
              Free under 5k members · No card required
            </p>
          </div>

          {/* Right — the Live Wire board, the anchor of the composition */}
          <div className="lg:-mr-4">
            <LiveWire />
          </div>
        </div>
      </section>

      {/* Stats — an instrument readout strip. */}
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

      {/* ============================================================ */}
      {/* ACT II — the pipeline. A real 3-step sequence, numbered.     */}
      {/* ============================================================ */}
      <section id="pipeline" className="mx-auto max-w-6xl scroll-mt-20 px-6 py-20">
        <div className="max-w-2xl">
          <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">
            Threat to record, in one pass
          </p>
          <h2 className="mt-3 font-display text-4xl font-semibold tracking-[-0.02em] text-foreground">
            Three seconds from arrival to filed.
          </h2>
        </div>

        <div className="mt-14 grid gap-px overflow-hidden rounded-lg border border-border bg-border md:grid-cols-3">
          {PIPELINE.map((step) => (
            <div key={step.n} className="relative bg-surface p-8">
              <span className="font-mono text-5xl font-semibold tracking-tight text-accent/25">{step.n}</span>
              <h3 className="mt-5 font-display text-xl font-semibold tracking-tight text-foreground">{step.head}</h3>
              <p className="mt-2.5 text-sm leading-relaxed text-muted">{step.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ============================================================ */}
      {/* ACT III — the record. ONE case file, in full.               */}
      {/* ============================================================ */}
      <section className="border-y border-border bg-surface">
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-6 py-20 lg:grid-cols-2">
          <div>
            <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">
              What’s left behind
            </p>
            <h2 className="mt-3 font-display text-4xl font-semibold tracking-[-0.02em] text-foreground">
              Every action becomes a file you can read back.
            </h2>
            <p className="mt-5 max-w-md text-base leading-relaxed text-muted">
              No disappearing DM logs, no “who muted this person and why.” The moment automod acts —
              or a moderator does — Docket opens a case with the evidence, the reason, and the rule
              or person behind it. Months later, it still reads clearly.
            </p>
            <Link
              href="/api/auth/discord/authorize"
              className={buttonVariants({ variant: 'subtle', size: 'md', className: 'mt-7 gap-2' })}
            >
              Open the caseload
              <ArrowRight className="size-4" />
            </Link>
          </div>

          {/* The case file — a single detailed record. */}
          <div className="rounded-lg border border-border bg-card">
            <div className="flex items-center justify-between border-b border-border px-5 py-3">
              <span className="font-mono text-xs font-semibold tracking-wide text-foreground">{CASE.ref}</span>
              <span className="font-mono text-[0.6875rem] uppercase tracking-[0.12em] text-muted-2">
                Filed {CASE.filed}
              </span>
            </div>
            <div className="space-y-4 p-5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-sm border border-threat/40 bg-threat-soft px-2 py-0.5 font-mono text-[0.625rem] font-bold uppercase tracking-[0.1em] text-threat">
                  {CASE.type}
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span className="tickmeter" style={{ ['--tick-color' as string]: 'var(--sev-critical)' }}>
                    <span className="tick on" /><span className="tick on" /><span className="tick on" /><span className="tick on" /><span className="tick on" />
                  </span>
                  <span className="font-mono text-[0.6875rem] uppercase tracking-wider text-threat">{CASE.severity}</span>
                </span>
              </div>

              <Field label="Subject">
                <span className="font-mono text-sm text-foreground">@{CASE.subject}</span>
              </Field>
              <Field label="Reason">
                <span className="text-sm leading-relaxed text-muted">{CASE.reason}</span>
              </Field>
              <Field label="Evidence">
                <span className="block rounded-sm bg-surface-2 px-2.5 py-1.5 font-mono text-xs text-muted line-through decoration-threat/50">
                  {CASE.evidence}
                </span>
              </Field>
              <Field label="Acted by">
                <span className="font-mono text-xs text-accent">{CASE.rule}</span>
              </Field>
            </div>
          </div>
        </div>
      </section>

      {/* Proof — filed quotes with the docket rail. */}
      <section id="testimonials" className="border-t border-border">
        <div className="mx-auto max-w-6xl px-6 py-20">
        <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-muted-2">
          On the record
        </p>
        <div className="mt-10 grid gap-px overflow-hidden rounded-lg border border-border bg-border md:grid-cols-3">
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
      <section className="border-t border-border">
        <div className="mx-auto max-w-4xl px-6 pb-24 pt-20 text-center">
          <h2 className="font-display text-4xl font-semibold tracking-[-0.02em] text-foreground sm:text-5xl">
            The next raid is already being planned.
          </h2>
          <p className="mx-auto mt-4 max-w-md text-lg text-muted">
            Deploy Docket in under 60 seconds and be ready before it lands.
          </p>
          <div className="mt-8 flex justify-center">
            <Link
              href="/api/auth/discord/authorize"
              className={buttonVariants({ variant: 'primary', size: 'lg', className: 'gap-2.5 px-8' })}
            >
              <LogIn className="size-4.5" /> Deploy Docket
            </Link>
          </div>
        </div>
      </section>
    </>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[88px_1fr] items-start gap-3">
      <span className="pt-0.5 font-mono text-[0.625rem] uppercase tracking-[0.14em] text-muted-2">{label}</span>
      <div className="min-w-0">{children}</div>
    </div>
  )
}
