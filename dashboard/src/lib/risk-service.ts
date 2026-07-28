import 'server-only'

import { createHash } from 'node:crypto'
import { botQuery } from '@/lib/bot-db'
import { resolveDiscordProfile, type ResolvedDiscordProfile } from '@/lib/discord'

export type RiskBreakdown = {
  score: number
  level: 'low' | 'medium' | 'high' | 'critical'
  factors: { name: string; points: number }[]
  lastCalculated: string | null
  stats: { warnings: number; violations30d: number; cases30d: number }
  recentViolations: { rule: string; severity: string; createdAt: string }[]
  member: ResolvedDiscordProfile
}

export function riskLevelFor(score: number): RiskBreakdown['level'] {
  if (score >= 80) return 'critical'
  if (score >= 60) return 'high'
  if (score >= 35) return 'medium'
  return 'low'
}

export async function getRiskBreakdown(guildId: string, userId: string): Promise<RiskBreakdown> {
  const [riskRows, warningRows, violationCountRows, caseCountRows, recentRows, member] = await Promise.all([
    botQuery<{ score: number; factors: string; last_calculated: Date | string }>(
      `SELECT score, factors::text, last_calculated FROM user_risk_scores
       WHERE guild_id = $1::bigint AND user_id = $2::bigint`,
      [guildId, userId],
    ),
    botQuery<{ value: string }>(
      `SELECT COUNT(*) AS value FROM warnings WHERE guild_id = $1::bigint AND user_id = $2::bigint`,
      [guildId, userId],
    ),
    botQuery<{ value: string }>(
      `SELECT COUNT(*) AS value FROM automod_events
       WHERE guild_id = $1::bigint AND user_id = $2::bigint AND created_at >= NOW() - INTERVAL '30 days'`,
      [guildId, userId],
    ),
    botQuery<{ value: string }>(
      `SELECT COUNT(*) AS value FROM cases
       WHERE guild_id = $1::bigint AND user_id = $2::bigint AND created_at >= NOW() - INTERVAL '30 days'`,
      [guildId, userId],
    ),
    botQuery<{ rule: string; severity: string; created_at: Date }>(
      `SELECT rule, severity, created_at FROM automod_events
       WHERE guild_id = $1::bigint AND user_id = $2::bigint
       ORDER BY created_at DESC LIMIT 5`,
      [guildId, userId],
    ),
    resolveDiscordProfile(guildId, userId),
  ])

  const row = riskRows[0]
  let factorsRaw: Record<string, number> = {}
  try { factorsRaw = JSON.parse(row?.factors || '{}') as Record<string, number> } catch { factorsRaw = {} }
  const factors = Object.entries(factorsRaw)
    .map(([name, points]) => ({ name, points: Number(points) || 0 }))
    .filter((factor) => factor.points > 0)
    .sort((a, b) => b.points - a.points)

  const score = Number(row?.score ?? 0)
  return {
    score,
    level: riskLevelFor(score),
    factors,
    lastCalculated: row?.last_calculated ? new Date(row.last_calculated).toISOString() : null,
    stats: {
      warnings: Number(warningRows[0]?.value ?? 0),
      violations30d: Number(violationCountRows[0]?.value ?? 0),
      cases30d: Number(caseCountRows[0]?.value ?? 0),
    },
    recentViolations: recentRows.map((violation) => ({
      rule: violation.rule,
      severity: violation.severity,
      createdAt: new Date(violation.created_at).toISOString(),
    })),
    member,
  }
}

const FACTOR_LABELS: Record<string, string> = {
  account_age: 'Very new Discord account',
  join_recent: 'Joined the server very recently',
  warnings: 'Active warnings on record',
  scam_history: 'Previously banned for scam links',
  default_avatar: 'No custom avatar',
  alt_suspicion: 'Flagged as a likely alt account',
  automod_violations: 'Recent AutoMod violations',
  recent_cases: 'Recent moderation cases',
}

function fallbackExplanation(breakdown: RiskBreakdown): string {
  if (breakdown.factors.length === 0) {
    return `${breakdown.member.displayName} scores ${breakdown.score}/100 — no active risk factors. This member has a clean recent record: no warnings, AutoMod violations, or cases in the last 30 days.`
  }
  const parts = breakdown.factors.slice(0, 4).map((factor) => {
    const label = FACTOR_LABELS[factor.name] ?? factor.name.replace(/_/g, ' ')
    return `${label.toLowerCase()} adds +${factor.points}`
  })
  const advice = breakdown.score >= 80
    ? 'Staff should watch this member closely and consider preemptive restrictions.'
    : breakdown.score >= 60
      ? 'Worth keeping an eye on — intervene early if behavior continues.'
      : breakdown.score >= 35
        ? 'Moderate risk; normal monitoring is enough for now.'
        : 'Low risk; no action needed.'
  return `${breakdown.member.displayName} scores ${breakdown.score}/100 (${breakdown.level}). ${parts.join('; ')}. ${advice}`
}

type ExplanationCacheEntry = { explanation: string; source: 'ai' | 'fallback'; generatedAt: string; expiresAt: number }
const explanationCache = new Map<string, ExplanationCacheEntry>()
const EXPLANATION_TTL_MS = 24 * 60 * 60_000

/** AI-generated staff explanation of a risk score, with a deterministic fallback. */
export async function explainRisk(breakdown: RiskBreakdown): Promise<{ explanation: string; source: 'ai' | 'fallback'; generatedAt: string }> {
  const fingerprint = createHash('sha1')
    .update(JSON.stringify([breakdown.score, breakdown.factors, breakdown.stats]))
    .digest('hex')
  const cacheKey = `${breakdown.member.id}:${fingerprint}`
  const cached = explanationCache.get(cacheKey)
  if (cached && cached.expiresAt > Date.now()) {
    return { explanation: cached.explanation, source: cached.source, generatedAt: cached.generatedAt }
  }

  const fallback = fallbackExplanation(breakdown)
  let result: { explanation: string; source: 'ai' | 'fallback' } = { explanation: fallback, source: 'fallback' }

  const apiKey = process.env.AIMODEL_API_KEY?.trim()
  if (apiKey) {
    const baseUrl = (process.env.AIMODEL_BASE_URL?.trim() || 'https://aimodel.lol/v1').replace(/\/+$/, '')
    const model = process.env.AIMODEL_CHAT_MODEL?.trim() || process.env.AI_MODEL?.trim() || 'accounts/aimodel/models/claude-fable-5'
    try {
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 20_000)
      const response = await fetch(`${baseUrl}/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
        signal: controller.signal,
        body: JSON.stringify({
          model,
          max_tokens: 220,
          messages: [
            {
              role: 'system',
              content: 'You are a moderation analyst for a Discord server. Explain a member\'s risk score to staff in 3-4 plain sentences: what drives it, how worried to be, and what to do next. Be concrete and calm. No markdown, no headers, no bullet lists.',
            },
            {
              role: 'user',
              content: JSON.stringify({
                member: breakdown.member.displayName,
                score: breakdown.score,
                level: breakdown.level,
                factors: breakdown.factors.map((factor) => ({ factor: FACTOR_LABELS[factor.name] ?? factor.name, points: factor.points })),
                warnings: breakdown.stats.warnings,
                automodViolations30d: breakdown.stats.violations30d,
                moderationCases30d: breakdown.stats.cases30d,
                recentViolationRules: breakdown.recentViolations.map((violation) => violation.rule),
              }),
            },
          ],
        }),
      })
      clearTimeout(timeout)
      if (response.ok) {
        const payload = await response.json() as { choices?: { message?: { content?: string } }[] }
        const text = payload.choices?.[0]?.message?.content?.trim()
        if (text) result = { explanation: text.slice(0, 1200), source: 'ai' }
      }
    } catch {
      // Fall back to the deterministic explanation below.
    }
  }

  const entry: ExplanationCacheEntry = {
    explanation: result.explanation,
    source: result.source,
    generatedAt: new Date().toISOString(),
    expiresAt: Date.now() + EXPLANATION_TTL_MS,
  }
  explanationCache.set(cacheKey, entry)
  return { explanation: entry.explanation, source: entry.source, generatedAt: entry.generatedAt }
}
