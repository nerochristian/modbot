import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok, created, parseListQuery, paginate } from '@/lib/api'
import { reportSchema } from '@/lib/validation'
import { logActivity } from '@/lib/log'
import type { Prisma } from '@prisma/client'

const SORTABLE = new Set(['name', 'type', 'status', 'createdAt'])

export async function GET(request: Request) {
  try {
    const guard = await requireUser('reports.read')
    if (guard instanceof Response) return guard

    const url = new URL(request.url)
    const query = parseListQuery(url, { defaultSort: 'createdAt' })

    const where: Prisma.ReportWhereInput = {}
    if (query.q) where.name = { contains: query.q }
    if (query.filters.type) where.type = query.filters.type
    if (query.filters.status) where.status = query.filters.status

    const sort = SORTABLE.has(query.sort) ? query.sort : 'createdAt'

    const [rows, total] = await Promise.all([
      prisma.report.findMany({
        where,
        orderBy: { [sort]: query.order },
        skip: (query.page - 1) * query.pageSize,
        take: query.pageSize,
        include: { createdBy: { select: { name: true } } },
      }),
      prisma.report.count({ where }),
    ])

    return ok(
      paginate(
        rows.map((r) => ({
          id: r.id,
          name: r.name,
          type: r.type,
          status: r.status,
          format: r.format,
          createdAt: r.createdAt.toISOString(),
          createdBy: r.createdBy?.name ?? 'System',
        })),
        total,
        query,
      ),
    )
  } catch (error) {
    return handleError(error)
  }
}

export async function POST(request: Request) {
  try {
    const guard = await requireUser('reports.write')
    if (guard instanceof Response) return guard
    const user = guard

    const body = await request.json()
    const data = reportSchema.parse(body)

    const report = await prisma.report.create({
      data: {
        name: data.name,
        type: data.type,
        format: data.format,
        status: 'ready',
        params: data.params ? JSON.stringify(data.params) : null,
        createdById: user.id,
      },
    })
    await logActivity({ userId: user.id, actorName: user.name, action: 'created_report', target: report.name })
    return created({ id: report.id, name: report.name })
  } catch (error) {
    return handleError(error)
  }
}
