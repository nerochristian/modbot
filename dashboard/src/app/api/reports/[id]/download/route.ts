import { prisma } from '@/lib/prisma'
import { requireUser, apiError } from '@/lib/api'
import { getMetricSeries } from '@/lib/metrics'

function toCsv(rows: Record<string, unknown>[]): string {
  if (rows.length === 0) return 'no data\n'
  const headers = Object.keys(rows[0])
  const escape = (v: unknown) => {
    const s = v == null ? '' : String(v)
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  return [headers.join(','), ...rows.map((r) => headers.map((h) => escape(r[h])).join(','))].join('\n')
}

// GET /api/reports/[id]/download — generate the report file on demand from live
// data so the download always reflects current numbers.
export async function GET(_request: Request, ctx: { params: Promise<{ id: string }> }) {
  const guard = await requireUser('reports.read')
  if (guard instanceof Response) return guard
  const { id } = await ctx.params

  const report = await prisma.report.findUnique({ where: { id } })
  if (!report) return apiError('Report not found', 404)
  // Object-level authorization: reports are per-user (the list route scopes by
  // createdById), so a user may only download their own report. Without this,
  // any reports.read user could download any report by guessing its id (IDOR).
  if (report.createdById !== guard.id) return apiError('Report not found', 404)

  let rows: Record<string, unknown>[] = []
  switch (report.type) {
    case 'actions': {
      const series = await getMetricSeries('actions', 90)
      rows = series.map((p) => ({ date: p.date.slice(0, 10), mod_actions: p.value }))
      break
    }
    case 'automod': {
      const series = await getMetricSeries('automodBlocks', 90)
      rows = series.map((p) => ({ date: p.date.slice(0, 10), automod_blocks: p.value }))
      break
    }
    case 'members':
    case 'activity':
    case 'custom':
    default: {
      const members = await prisma.member.findMany({ take: 500, orderBy: { warnings: 'desc' } })
      rows = members.map((m) => ({
        username: m.username,
        display_name: m.displayName,
        discord_id: m.discordId,
        standing: m.standing,
        risk_level: m.riskLevel,
        warnings: m.warnings,
        messages: m.messages,
      }))
    }
  }

  const csv = toCsv(rows)
  const filename = `${report.name.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}.csv`
  return new Response(csv, {
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': `attachment; filename="${filename}"`,
    },
  })
}
