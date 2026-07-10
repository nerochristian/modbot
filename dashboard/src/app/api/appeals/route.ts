import { handleError, ok, paginate, parseListQuery, requireUser } from '@/lib/api'

export async function GET(request: Request) {
  try {
    const guard = await requireUser('appeals.read')
    if (guard instanceof Response) return guard
    const query = parseListQuery(new URL(request.url), { defaultSort: 'submittedAt', maxPageSize: 100 })
    return ok({ ...paginate([], 0, query), pending: 0 })
  } catch (error) {
    return handleError(error)
  }
}
