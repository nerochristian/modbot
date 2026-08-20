import type { ReactNode } from 'react'
import {
  Ban,
  AlertTriangle,
  CheckCircle2,
  Flag,
  LifeBuoy,
  ScrollText,
  MoreHorizontal,
  Radar,
  Archive,
  PartyPopper,
} from 'lucide-react'
import { Stamp } from '@/components/ui/stamp'
import { TickMeter } from '@/components/ui/badge'

/**
 * The dense, "living widget" feature showcase — every sub-feature pairs a
 * plain description with a small static mockup of the actual product
 * surface (a case ledger row, a ticket category picker, a risk read),
 * instead of an icon-and-sentence card grid.
 */

type SubFeature = {
  title: string
  desc: string
  widget: ReactNode
}

type Category = {
  name: string
  tagline: string
  items: SubFeature[]
}

function WidgetFrame({ children }: { children: ReactNode }) {
  return <div className="mt-4 rounded-lg border border-border bg-surface-2/60 p-3">{children}</div>
}

const CATEGORIES: Category[] = [
  {
    name: 'Moderation & security',
    tagline: 'The stuff that has to happen before a human even sees the message.',
    items: [
      {
        title: 'Automod',
        desc: 'Filters spam, scam links, and raid patterns in real time, tuned per server.',
        widget: (
          <WidgetFrame>
            <div className="flex items-center gap-2 text-xs">
              <Ban className="size-3.5 shrink-0 text-threat" />
              <span className="min-w-0 flex-1 truncate text-foreground">Scam link removed</span>
              <span className="shrink-0 text-muted-2">#general</span>
            </div>
            <div className="mt-2 flex items-center gap-2 text-xs">
              <AlertTriangle className="size-3.5 shrink-0 text-warning" />
              <span className="min-w-0 flex-1 truncate text-foreground">Caps flood muted 10m</span>
              <span className="shrink-0 text-muted-2">#chat</span>
            </div>
          </WidgetFrame>
        ),
      },
      {
        title: 'Protection',
        desc: 'Anti-raid, alt-account detection, and a link allowlist that watches the whole server.',
        widget: (
          <WidgetFrame>
            <div className="space-y-1.5">
              {['Anti-raid', 'Alt detection', 'Link filter'].map((label) => (
                <div
                  key={label}
                  className="flex items-center justify-between rounded-md border border-border bg-card px-2.5 py-1.5 text-xs"
                >
                  <span className="text-foreground">{label}</span>
                  <span className="flex items-center gap-1 text-[0.6875rem] font-medium text-success">
                    <CheckCircle2 className="size-3.5" />
                    On
                  </span>
                </div>
              ))}
            </div>
          </WidgetFrame>
        ),
      },
      {
        title: 'Cases',
        desc: 'Every ban, mute, and warning lands as a record with a reason and a moderator.',
        widget: (
          <WidgetFrame>
            <ul className="space-y-2 text-xs">
              <li className="flex items-center justify-between gap-2">
                <span className="min-w-0 truncate text-foreground">Ban · raid alt</span>
                <Stamp id="CASE-0421" />
              </li>
              <li className="flex items-center justify-between gap-2">
                <span className="min-w-0 truncate text-foreground">Warn · slur filter</span>
                <Stamp id="CASE-0417" />
              </li>
            </ul>
          </WidgetFrame>
        ),
      },
    ],
  },
  {
    name: 'Reports, tickets & appeals',
    tagline: 'A place for members to raise something, and staff to work it without the public thread.',
    items: [
      {
        title: 'Reports',
        desc: 'Members flag trouble privately; staff triage in a queue with one-click actions.',
        widget: (
          <WidgetFrame>
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-foreground">Member reported</span>
              <span className="text-muted-2">Harassment</span>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {['Warn', 'Timeout', 'Dismiss'].map((a) => (
                <span key={a} className="rounded-md border border-border bg-card px-2 py-1 text-[0.6875rem] text-muted">
                  {a}
                </span>
              ))}
            </div>
          </WidgetFrame>
        ),
      },
      {
        title: 'Tickets',
        desc: 'Support and appeals move into a private channel, with a transcript kept.',
        widget: (
          <WidgetFrame>
            <div className="grid grid-cols-2 gap-1.5">
              {[
                { icon: LifeBuoy, label: 'Support' },
                { icon: Flag, label: 'Report' },
                { icon: ScrollText, label: 'Appeal' },
                { icon: MoreHorizontal, label: 'Other' },
              ].map((c) => (
                <div
                  key={c.label}
                  className="flex items-center gap-1.5 rounded-md border border-border bg-card px-2 py-1.5 text-[0.6875rem] text-foreground"
                >
                  <c.icon className="size-3.5 shrink-0 text-accent" />
                  {c.label}
                </div>
              ))}
            </div>
          </WidgetFrame>
        ),
      },
      {
        title: 'Appeals',
        desc: 'A real process for members to contest a decision — reviewed, not ignored.',
        widget: (
          <WidgetFrame>
            <div className="flex items-center justify-between text-xs">
              <span className="text-foreground">Appeal #112</span>
              <span className="font-medium text-success">Approved</span>
            </div>
            <div className="mt-1.5 flex items-center justify-between text-xs">
              <span className="text-foreground">Appeal #109</span>
              <span className="font-medium text-threat">Denied</span>
            </div>
          </WidgetFrame>
        ),
      },
    ],
  },
  {
    name: 'Utility & insight',
    tagline: 'What keeps the rest of the bot honest — and gives everyone something to do besides moderate.',
    items: [
      {
        title: 'Risk scoring',
        desc: 'New and returning members get a risk read from account age and history.',
        widget: (
          <WidgetFrame>
            <div className="flex items-center justify-between text-xs">
              <span className="font-mono text-foreground">@Newcomer</span>
              <TickMeter severity="low" />
            </div>
            <div className="mt-1.5 flex items-center justify-between text-xs">
              <span className="font-mono text-foreground">@Vandalizer</span>
              <TickMeter severity="critical" />
            </div>
          </WidgetFrame>
        ),
      },
      {
        title: 'Server backup',
        desc: 'Roles, channels, and settings snapshotted, with one-click restore.',
        widget: (
          <WidgetFrame>
            <div className="flex items-center justify-between text-xs text-muted-2">
              <span className="flex items-center gap-1.5 text-foreground">
                <Archive className="size-3.5 text-accent" />
                Last backup
              </span>
              <span>2h ago</span>
            </div>
            <div className="mt-2 flex gap-3 font-mono text-[0.6875rem] text-muted">
              <span>42 channels</span>
              <span>18 roles</span>
            </div>
          </WidgetFrame>
        ),
      },
      {
        title: 'Giveaways & polls',
        desc: 'Run a giveaway or a poll without leaving Discord — Docket tracks entries and closes it on time.',
        widget: (
          <WidgetFrame>
            <div className="flex items-center gap-2 text-xs">
              <PartyPopper className="size-3.5 shrink-0 text-accent" />
              <span className="min-w-0 flex-1 truncate font-semibold text-foreground">Nitro giveaway</span>
              <span className="shrink-0 text-muted-2">2d 14h left</span>
            </div>
            <p className="mt-1.5 flex items-center gap-1.5 text-[0.6875rem] text-muted-2">
              <Radar className="size-3 shrink-0" />
              128 entries
            </p>
          </WidgetFrame>
        ),
      },
    ],
  },
]

export function FeatureShowcase() {
  return (
    <div className="space-y-16">
      {CATEGORIES.map((cat) => (
        <div key={cat.name}>
          <h3 className="font-display text-xl font-semibold text-foreground">{cat.name}</h3>
          <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-muted">{cat.tagline}</p>
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {cat.items.map((item) => (
              <div key={item.title} className="lift-card rounded-2xl border border-border bg-card p-5">
                <h4 className="font-display text-base font-semibold text-foreground">{item.title}</h4>
                <p className="mt-1.5 text-[0.8125rem] leading-relaxed text-muted">{item.desc}</p>
                {item.widget}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
