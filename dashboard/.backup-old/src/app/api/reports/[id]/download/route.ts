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

  let rows: Record<string, unknown>[] = []
  switch (report.type) {
    case 'revenue': {
      const series = await getMetricSeries('revenue', 90)
      rows = series.map((p) => ({ date: p.date.slice(0, 10), revenue: p.value }))
      break
    }
    case 'retention': {
      const series = await getMetricSeries('retention', 90)
      rows = series.map((p) => ({ date: p.date.slice(0, 10), retention_pct: p.value }))
      break
    }
    case 'users':
    case 'activity':
    case 'custom':
    default: {
      const customers = await prisma.customer.findMany({ take: 500, orderBy: { mrr: 'desc' } })
      rows = customers.map((c) => ({
        name: c.name,
        email: c.email,
        company: c.company ?? '',
        plan: c.plan,
        status: c.status,
        mrr_usd: (c.mrr / 100).toFixed(2),
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
