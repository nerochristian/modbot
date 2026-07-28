'use client'

import { useEffect, useState } from 'react'
import { ShieldQuestion, Sparkles } from 'lucide-react'
import { Modal } from '@/components/ui/modal'
import { Badge, TickMeter, severityTone } from '@/components/ui/badge'
import { Avatar } from '@/components/ui/avatar'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { formatDistanceToNow } from 'date-fns'

export type RiskBreakdownPayload = {
  score: number
  level: 'low' | 'medium' | 'high' | 'critical'
  factors: { name: string; points: number }[]
  lastCalculated: string | null
  stats: { warnings: number; violations30d: number; cases30d: number }
  recentViolations: { rule: string; severity: string; createdAt: string }[]
  member: { id: string; username: string; displayName: string; nickname: string | null; avatarUrl: string }
  explanation?: { explanation: string; source: 'ai' | 'fallback'; generatedAt: string }
}

const FACTOR_LABELS: Record<string, string> = {
  account_age: 'New Discord account',
  join_recent: 'Just joined the server',
  warnings: 'Warnings on record',
  scam_history: 'Scam-link history',
  default_avatar: 'Default avatar',
  alt_suspicion: 'Likely alt account',
  automod_violations: 'AutoMod violations (30d)',
  recent_cases: 'Moderation cases (30d)',
}

/**
 * Click-any-risk-score target: shows exactly why the score is what it is,
 * plus an AI-written staff summary.
 */
export function RiskBreakdownModal({ memberId, onClose }: { memberId: string; onClose: () => void }) {
  const [data, setData] = useState<RiskBreakdownPayload | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetch(`/api/members/${memberId}/risk`, { method: 'POST', signal: controller.signal })
      .then(async (res) => {
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(body.error ?? 'Could not load the risk breakdown')
        setData(body as RiskBreakdownPayload)
      })
      .catch((err) => {
        if (err?.name !== 'AbortError') setError(err instanceof Error ? err.message : 'Could not load the risk breakdown')
      })
    return () => controller.abort()
  }, [memberId])

  const maxPoints = data?.factors[0]?.points ?? 1

  return (
    <Modal open onClose={onClose} title="Risk score breakdown" size="lg" footer={<Button variant="ghost" onClick={onClose}>Close</Button>}>
      {error ? (
        <p className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>
      ) : !data ? (
        <div className="space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : (
        <div className="space-y-5">
          {/* Score header */}
          <div className="flex items-center gap-4">
            <Avatar name={data.member.displayName} src={data.member.avatarUrl} size="lg" />
            <div className="min-w-0 flex-1">
              <p className="truncate font-display font-semibold text-foreground">{data.member.nickname || data.member.displayName}</p>
              <p className="truncate text-xs text-muted">@{data.member.username}</p>
            </div>
            <div className="text-right">
              <p className="font-display text-3xl font-semibold tabular-nums text-foreground">{data.score}<span className="text-base text-muted-2">/100</span></p>
              <div className="mt-1 flex items-center justify-end gap-2">
                <TickMeter severity={data.level} />
                <Badge tone={severityTone(data.level)}>{data.level}</Badge>
              </div>
            </div>
          </div>

          {/* Why — factor rows */}
          <div>
            <p className="mb-2 font-mono text-[0.625rem] font-bold uppercase tracking-[0.18em] text-accent">Why this score</p>
            {data.factors.length === 0 ? (
              <p className="rounded-lg border border-border bg-surface-2/50 px-3 py-2 text-sm text-muted">
                No active risk factors — clean recent record.
              </p>
            ) : (
              <ul className="space-y-2">
                {data.factors.map((factor) => (
                  <li key={factor.name} className="flex items-center gap-3">
                    <span className="w-44 shrink-0 truncate text-sm text-foreground">{FACTOR_LABELS[factor.name] ?? factor.name.replace(/_/g, ' ')}</span>
                    <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-2">
                      <span
                        className="block h-full rounded-full bg-accent transition-all duration-500"
                        style={{ width: `${Math.max(6, (factor.points / maxPoints) * 100)}%` }}
                      />
                    </span>
                    <span className="w-10 shrink-0 text-right font-mono text-xs font-semibold text-muted">+{factor.points}</span>
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-3 flex flex-wrap gap-1.5 text-xs">
              <Badge tone="neutral">{data.stats.warnings} warnings</Badge>
              <Badge tone="neutral">{data.stats.violations30d} automod hits / 30d</Badge>
              <Badge tone="neutral">{data.stats.cases30d} cases / 30d</Badge>
              {data.lastCalculated && (
                <span className="ml-auto text-muted-2">
                  recalculated {formatDistanceToNow(new Date(data.lastCalculated), { addSuffix: true })}
                </span>
              )}
            </div>
          </div>

          {/* AI explanation */}
          <div className="rounded-xl border border-accent-line bg-accent-soft/30 p-4">
            <div className="flex items-center gap-2">
              <Sparkles className="size-4 text-accent" />
              <p className="text-sm font-medium text-foreground">Staff summary</p>
              {data.explanation && (
                <Badge tone={data.explanation.source === 'ai' ? 'accent' : 'neutral'}>
                  {data.explanation.source === 'ai' ? 'AI-written' : 'Auto summary'}
                </Badge>
              )}
            </div>
            {data.explanation ? (
              <p className="mt-2 text-sm leading-6 text-muted">{data.explanation.explanation}</p>
            ) : (
              <div className="mt-2 space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            )}
          </div>

          {/* Recent violations */}
          {data.recentViolations.length > 0 && (
            <div>
              <p className="mb-2 flex items-center gap-2 font-mono text-[0.625rem] font-bold uppercase tracking-[0.18em] text-accent">
                <ShieldQuestion className="size-3.5" /> Latest AutoMod hits
              </p>
              <ul className="divide-y divide-border rounded-lg border border-border">
                {data.recentViolations.map((violation, index) => (
                  <li key={index} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                    <span className="text-foreground">{violation.rule.replace(/_/g, ' ')}</span>
                    <span className="flex items-center gap-2">
                      <Badge tone={severityTone(violation.severity)}>{violation.severity}</Badge>
                      <span className="text-xs text-muted-2">{formatDistanceToNow(new Date(violation.createdAt), { addSuffix: true })}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}
