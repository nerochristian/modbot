import type { Metadata } from 'next'
import Link from 'next/link'
import {
  Activity,
  ArrowRight,
  Bot,
  Check,
  Clock3,
  FileText,
  Gavel,
  LayoutDashboard,
  MessageSquareWarning,
  Scale,
  ShieldCheck,
  Users,
  Zap,
} from 'lucide-react'
import { Badge, TickMeter } from '@/components/ui/badge'
import { buttonVariants } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export const metadata: Metadata = {
  title: 'Docket — Discord moderation workspace',
  description:
    'Manage automod, cases, appeals, members, and moderation activity from one Discord workspace.',
}

const chartBars = [42, 58, 36, 72, 55, 84, 61, 48, 76, 64, 92, 68, 79, 56]

const activityRows = [
  { actor: 'Alex P.', action: 'Timed out', target: '@mixer_07', time: '2m ago', tone: 'warning' as const },
  { actor: 'Docket', action: 'Blocked link burst from', target: '@nightshift', time: '8m ago', tone: 'accent' as const },
  { actor: 'Mina K.', action: 'Resolved appeal for', target: '@solace', time: '14m ago', tone: 'success' as const },
]

const features = [
  {
    icon: MessageSquareWarning,
    title: 'Automod you can explain',
    description: 'Build readable rules, preview their effect, and keep every automated action in the audit trail.',
  },
  {
    icon: Gavel,
    title: 'Cases with full context',
    description: 'Messages, member history, moderator notes, and actions stay together from open to resolved.',
  },
  {
    icon: Scale,
    title: 'Appeals beside the decision',
    description: 'Review the original evidence and the member response without switching tools or chasing screenshots.',
  },
]

function MiniStat({ label, value, icon: Icon }: { label: string; value: string; icon: typeof Activity }) {
  return (
    <div className="rounded-xl border border-border bg-card p-3.5 shadow-[0_16px_42px_-32px_rgba(0,0,0,.7)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[0.5625rem] font-semibold uppercase tracking-[0.1em] text-muted">{label}</p>
          <p className="mt-2 font-display text-xl font-semibold leading-none text-foreground">{value}</p>
        </div>
        <span className="grid size-8 place-items-center rounded-lg bg-accent-soft text-accent">
          <Icon className="size-4" />
        </span>
      </div>
    </div>
  )
}

function DashboardPreview() {
  return (
    <Card className="relative overflow-hidden border-border-strong bg-surface/92 shadow-[0_35px_100px_-50px_rgba(18,30,62,.55)]">
      <div className="flex h-12 items-center gap-2 border-b border-border bg-surface/80 px-3.5">
        <span className="grid size-7 place-items-center rounded-lg border border-accent-line bg-accent-soft font-display text-[0.5625rem] font-bold text-accent">NO</span>
        <div>
          <p className="text-[0.6875rem] font-semibold text-foreground">Nova Community</p>
          <p className="text-[0.5625rem] text-muted-2">Moderation overview</p>
        </div>
        <span className="ml-auto flex items-center gap-1.5 rounded-lg border border-border bg-surface-2 px-2 py-1 font-mono text-[0.5625rem] text-muted">
          <span className="size-1.5 rounded-full bg-success" /> Live
        </span>
      </div>
      <div className="grid min-h-[450px] md:grid-cols-[138px_minmax(0,1fr)]">
        <aside className="hidden border-r border-border bg-surface/72 p-3 md:block">
          <p className="px-2 font-mono text-[0.5rem] font-semibold uppercase tracking-[0.14em] text-muted-2">Moderation</p>
          <div className="mt-2 space-y-1">
            {[
              [LayoutDashboard, 'Overview'],
              [Users, 'Members'],
              [Gavel, 'Cases'],
              [ShieldCheck, 'Automod'],
              [Activity, 'Activity'],
            ].map(([Icon, label], index) => (
              <div
                key={label as string}
                className={`flex h-8 items-center gap-2 rounded-lg px-2 text-[0.625rem] font-medium ${index === 0 ? 'border border-accent-line bg-accent-soft text-foreground' : 'text-muted'}`}
              >
                <Icon className={`size-3.5 ${index === 0 ? 'text-accent' : 'text-muted-2'}`} />
                {label as string}
              </div>
            ))}
          </div>
        </aside>
        <div className="min-w-0 bg-paper/55 p-3.5 sm:p-4">
          <div className="mb-3 flex items-end justify-between gap-3 border-b border-border pb-3">
            <div>
              <p className="font-mono text-[0.5rem] font-semibold uppercase tracking-[0.16em] text-accent">Workspace</p>
              <p className="mt-1 font-display text-base font-semibold text-foreground">Good afternoon, Alex</p>
            </div>
            <Badge tone="success" dot className="text-[0.5625rem]">Operational</Badge>
          </div>
          <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-4">
            <MiniStat label="Open cases" value="12" icon={Gavel} />
            <MiniStat label="Members" value="8.4k" icon={Users} />
            <MiniStat label="Automod today" value="36" icon={ShieldCheck} />
            <MiniStat label="Pending appeals" value="3" icon={Scale} />
          </div>
          <div className="mt-2.5 grid gap-2.5 lg:grid-cols-[1.35fr_.65fr]">
            <div className="rounded-xl border border-border bg-card p-3.5">
              <div className="flex items-center justify-between">
                <p className="text-[0.6875rem] font-semibold text-foreground">Moderation actions</p>
                <span className="font-mono text-[0.5rem] text-muted-2">LAST 14 DAYS</span>
              </div>
              <div className="mt-5 flex h-24 items-end gap-1.5 border-b border-border px-1">
                {chartBars.map((height, index) => (
                  <span
                    key={index}
                    className="min-w-0 flex-1 rounded-t-sm bg-accent/75"
                    style={{ height: `${height}%`, opacity: 0.45 + index / 28 }}
                  />
                ))}
              </div>
            </div>
            <div className="rounded-xl border border-border bg-card p-3.5">
              <div className="flex items-center justify-between">
                <p className="text-[0.6875rem] font-semibold text-foreground">Bot status</p>
                <Bot className="size-3.5 text-accent" />
              </div>
              <div className="mt-4 space-y-3">
                {['Gateway', 'Automod', 'Database'].map((service) => (
                  <div key={service} className="flex items-center justify-between text-[0.625rem]">
                    <span className="flex items-center gap-2 text-foreground"><i className="size-1.5 rounded-full bg-success" />{service}</span>
                    <span className="text-muted">Online</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="mt-2.5 rounded-xl border border-border bg-card p-3.5">
            <div className="flex items-center justify-between">
              <p className="text-[0.6875rem] font-semibold text-foreground">Recent activity</p>
              <span className="text-[0.5625rem] font-medium text-accent">View all</span>
            </div>
            <div className="mt-2 divide-y divide-border">
              {activityRows.slice(0, 2).map((row) => (
                <div key={row.target} className="flex items-center gap-2 py-2 text-[0.625rem]">
                  <span className="grid size-6 place-items-center rounded-lg bg-surface-2 font-mono text-[0.5rem] font-semibold text-muted">{row.actor.slice(0, 2).toUpperCase()}</span>
                  <span className="min-w-0 truncate text-muted"><strong className="font-medium text-foreground">{row.actor}</strong> {row.action.toLowerCase()} <span className="font-mono text-foreground">{row.target}</span></span>
                  <span className="ml-auto shrink-0 text-muted-2">{row.time}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Card>
  )
}

export default function LandingPage() {
  return (
    <>
      <section className="px-4 pb-20 pt-16 sm:px-6 sm:pt-24 lg:px-8 lg:pb-28">
        <div className="mx-auto grid max-w-[1440px] items-center gap-14 xl:grid-cols-[0.82fr_1.18fr] xl:gap-16">
          <div className="max-w-2xl">
            <Badge tone="accent" dot className="font-mono text-[0.6875rem] uppercase tracking-[0.1em]">
              Discord moderation workspace
            </Badge>
            <h1 className="mt-6 font-display text-5xl font-semibold leading-[0.96] tracking-[-0.045em] text-foreground sm:text-6xl lg:text-7xl">
              Keep moderation clear, even when chat isn&apos;t.
            </h1>
            <p className="mt-6 max-w-xl text-base leading-7 text-muted sm:text-lg">
              Docket brings automod, cases, member history, appeals, and team activity into one workspace built for Discord moderators.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link href="/api/auth/discord/authorize" className={buttonVariants({ size: 'lg' })}>
                Sign in with Discord
                <ArrowRight className="size-4.5" />
              </Link>
              <a href="#overview" className={buttonVariants({ variant: 'outline', size: 'lg' })}>
                See what&apos;s inside
              </a>
            </div>
            <div className="mt-8 flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted">
              {['Uses Discord permissions', 'No card required', 'Setup in minutes'].map((item) => (
                <span key={item} className="flex items-center gap-2"><Check className="size-4 text-success" />{item}</span>
              ))}
            </div>
          </div>
          <div className="relative">
            <div className="pointer-events-none absolute -inset-8 -z-10 rounded-[2rem] bg-accent-soft blur-3xl" />
            <DashboardPreview />
          </div>
        </div>
      </section>

      <section id="overview" className="scroll-mt-24 border-y border-border bg-surface/35 px-4 py-20 sm:px-6 lg:px-8 lg:py-24">
        <div className="mx-auto max-w-[1440px]">
          <div className="max-w-2xl">
            <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">Everything on one docket</p>
            <h2 className="mt-3 font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">The same calm workspace for every moderation decision.</h2>
            <p className="mt-4 text-base leading-7 text-muted">Your team sees the rule, the evidence, the action, and the follow-up in one consistent system.</p>
          </div>
          <div className="mt-10 grid gap-4 lg:grid-cols-3">
            {features.map((feature) => (
              <Card key={feature.title} className="lift-card h-full">
                <CardContent className="p-6">
                  <span className="grid size-11 place-items-center rounded-xl border border-accent-line bg-accent-soft text-accent">
                    <feature.icon className="size-5" />
                  </span>
                  <h3 className="mt-5 font-display text-xl font-semibold text-foreground">{feature.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-muted">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section id="workflow" className="scroll-mt-24 px-4 py-20 sm:px-6 lg:px-8 lg:py-28">
        <div className="mx-auto grid max-w-[1440px] gap-10 lg:grid-cols-[0.72fr_1.28fr] lg:items-center lg:gap-16">
          <div>
            <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">From signal to record</p>
            <h2 className="mt-3 font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">A workflow your whole mod team can follow.</h2>
            <p className="mt-4 text-base leading-7 text-muted">Automod catches the signal. A moderator reviews the context. Docket records the decision and keeps the appeal attached.</p>
            <div className="mt-7 space-y-4">
              {[
                [Zap, 'Detect', 'Catch spam, raids, harmful links, and repeat behavior.'],
                [ShieldCheck, 'Review', 'See the messages and member history before acting.'],
                [FileText, 'Record', 'Save the action, reason, evidence, and moderator.'],
              ].map(([Icon, title, description]) => (
                <div key={title as string} className="flex gap-3">
                  <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-accent-soft text-accent"><Icon className="size-4" /></span>
                  <div><p className="text-sm font-semibold text-foreground">{title as string}</p><p className="mt-1 text-sm text-muted">{description as string}</p></div>
                </div>
              ))}
            </div>
          </div>
          <Card className="overflow-hidden">
            <CardHeader className="items-center border-b border-border pb-4">
              <div>
                <p className="font-mono text-[0.625rem] font-semibold uppercase tracking-[0.14em] text-accent">Active caseload</p>
                <CardTitle className="mt-1 text-base">Items that need a decision</CardTitle>
              </div>
              <Badge tone="info">7 open</Badge>
            </CardHeader>
            <div className="overflow-x-auto">
              <div className="min-w-[660px]">
                <div className="grid grid-cols-[1fr_1fr_1.35fr_.7fr] gap-4 bg-surface-2 px-5 py-2.5 font-mono text-[0.625rem] font-semibold uppercase tracking-[0.08em] text-muted-2">
                  <span>Signal</span><span>Member</span><span>Context</span><span>Status</span>
                </div>
                {[
                  ['high', 'Raid cluster', '@mixer_07 + 2', '8 duplicate links / 3 channels', 'Contained', 'success'],
                  ['medium', 'Ban evasion', '@nightshift', 'Matched prior account fingerprint', 'Review', 'warning'],
                  ['low', 'Member report', '@solace', '4 messages attached as evidence', 'Open', 'info'],
                ].map(([severity, signal, member, context, status, tone]) => (
                  <div key={member} className="grid grid-cols-[1fr_1fr_1.35fr_.7fr] items-center gap-4 border-t border-border px-5 py-4 text-sm">
                    <span className="flex items-center gap-3 font-medium text-foreground"><TickMeter severity={severity} />{signal}</span>
                    <span className="font-mono text-xs text-foreground">{member}</span>
                    <span className="text-muted">{context}</span>
                    <Badge tone={tone as 'success' | 'warning' | 'info'}>{status}</Badge>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2 border-t border-border bg-surface-2/55 px-5 py-3 text-xs text-muted">
              <Clock3 className="size-3.5" /> Every action keeps its timestamp, moderator, reason, and evidence.
            </div>
          </Card>
        </div>
      </section>

      <section className="px-4 pb-20 sm:px-6 lg:px-8 lg:pb-28">
        <Card className="mx-auto max-w-[1440px] overflow-hidden border-accent-line bg-accent-soft/55">
          <CardContent className="flex flex-col items-start justify-between gap-7 p-8 sm:p-10 lg:flex-row lg:items-center lg:p-12">
            <div className="max-w-2xl">
              <Badge tone="success" dot>Bot and dashboard connected</Badge>
              <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">Put your moderation workspace in order.</h2>
              <p className="mt-3 text-base text-muted">Connect Discord, choose a server, and start with the tools your team already has permission to use.</p>
            </div>
            <Link href="/api/auth/discord/authorize" className={buttonVariants({ size: 'lg', className: 'shrink-0' })}>
              Open Docket
              <ArrowRight className="size-4.5" />
            </Link>
          </CardContent>
        </Card>
      </section>
    </>
  )
}
