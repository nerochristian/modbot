import { handleError, ok, paginate, parseListQuery, requireUser } from '@/lib/api'
import { listGuildAppeals } from '@/lib/appeals-service'

export async function GET(request: Request) {
  try {
    const guard = await requireUser('appeals.read')
    if (guard instanceof Response) return guard
    const query = parseListQuery(new URL(request.url), { defaultSort: 'submittedAt', maxPageSize: 100 })
    const result = await listGuildAppeals(guard.selectedGuildId!, query)
    return ok({ ...paginate(result.data, result.total, query), pending: result.pending })
  } catch (error) {
    return handleError(error)
  }
}
