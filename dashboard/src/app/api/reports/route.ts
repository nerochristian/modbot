import { created, handleError, ok, paginate, parseListQuery, requireMutation, requireUser } from '@/lib/api'
import { createGuildReport, listGuildReports } from '@/lib/reports-service'
import { reportSchema } from '@/lib/validation'

export async function GET(request: Request) {
  try {
    const guard = await requireUser('reports.read')
    if (guard instanceof Response) return guard
    const query = parseListQuery(new URL(request.url), { defaultSort: 'createdAt' })
    const result = await listGuildReports(guard.selectedGuildId!, guard.id, query)
    return ok(paginate(result.data, result.total, query))
  } catch (error) {
    return handleError(error)
  }
}

export async function POST(request: Request) {
  try {
    const guard = await requireMutation(request, 'reports.write')
    if (guard instanceof Response) return guard
    const data = reportSchema.parse(await request.json())
    const report = await createGuildReport({
      guildId: guard.selectedGuildId!,
      userId: guard.id,
      userName: guard.name,
      name: data.name,
      type: data.type,
      format: data.format,
      params: data.params,
    })
    return created(report)
  } catch (error) {
    return handleError(error)
  }
}
