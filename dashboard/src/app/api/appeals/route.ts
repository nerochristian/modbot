import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok, parseListQuery, paginate } from '@/lib/api'
import type { Prisma } from '@prisma/client'

const SORTABLE = new Set(['ref', 'status', 'submittedAt'])

export async function GET(request: Request) {
  try {
    const guard = await requireUser('appeals.read')
    if (guard instanceof Response) return guard

    const url = new URL(request.url)
    const query = parseListQuery(url, { defaultSort: 'submittedAt', maxPageSize: 100 })

    const where: Prisma.AppealWhereInput = {}
    if (query.q) {
      const or: Prisma.AppealWhereInput[] = [{ message: { contains: query.q } }]
      if (/^\d+$/.test(query.q)) or.push({ ref: Number(query.q) })
      where.OR = or
    }
    if (query.filters.status) where.status = query.filters.status

    const sort = SORTABLE.has(query.sort) ? query.sort : 'submittedAt'

    const [rows, total, pending] = await Promise.all([
      prisma.appeal.findMany({
        where,
        orderBy: { [sort]: query.order },
        skip: (query.page - 1) * query.pageSize,
        take: query.pageSize,
        include: {
          member: { select: { id: true, username: true, displayName: true, discordId: true, avatarColor: true } },
          case: { select: { id: true, ref: true, type: true, severity: true, reason: true } },
        },
      }),
      prisma.appeal.count({ where }),
      prisma.appeal.count({ where: { status: 'pending' } }),
    ])

    return ok({ ...paginate(rows, total, query), pending })
  } catch (error) {
    return handleError(error)
  }
}
