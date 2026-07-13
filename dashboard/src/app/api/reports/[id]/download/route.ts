import { apiError, handleError, requireUser } from '@/lib/api'
import { buildReportArtifact } from '@/lib/report-formatters'
import { getGuildReport, getGuildReportRows } from '@/lib/reports-service'

function safeFilename(value: string): string {
  return value.normalize('NFKD').replace(/[^a-z0-9]+/gi, '-').replace(/^-+|-+$/g, '').toLowerCase() || 'report'
}

export async function GET(_request: Request, ctx: RouteContext<'/api/reports/[id]/download'>) {
  try {
    const guard = await requireUser('reports.read')
    if (guard instanceof Response) return guard
    const { id } = await ctx.params
    if (!/^\d+$/.test(id)) return apiError('Report not found', 404)
    const report = await getGuildReport(guard.selectedGuildId!, guard.id, id)
    if (!report) return apiError('Report not found', 404)
    const rows = await getGuildReportRows(report)
    const artifact = await buildReportArtifact(report.format, report.name, rows)
    const filename = `${safeFilename(report.name)}.${artifact.extension}`
    return new Response(new Uint8Array(artifact.body), {
      headers: {
        'Content-Type': artifact.contentType,
        'Content-Disposition': `attachment; filename="${filename}"`,
        'Cache-Control': 'private, no-store, max-age=0',
        'X-Content-Type-Options': 'nosniff',
      },
    })
  } catch (error) {
    return handleError(error)
  }
}
