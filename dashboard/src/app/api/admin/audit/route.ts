import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok, parseListQuery, paginate } from '@/lib/api'
import { parseJson } from '@/lib/json'
import type { Prisma } from '@prisma/client'

export async function GET(request: Request) {
  try {
    const guard = await requireUser('audit.read')
    if (guard instanceof Response) return guard
    const guildId = guard.selectedGuildId as string

    const url = new URL(request.url)
    const query = parseListQuery(url, { defaultSort: 'createdAt', maxPageSize: 50 })

    const where: Prisma.AuditLogWhereInput = { guildId }
    if (query.q) {
      where.OR = [
        { actorName: { contains: query.q } },
        { action: { contains: query.q } },
        { entity: { contains: query.q } },
      ]
    }
    if (query.filters.entity) where.entity = query.filters.entity

    const [rows, total] = await Promise.all([
      prisma.auditLog.findMany({
        where,
        orderBy: { createdAt: 'desc' },
        skip: (query.page - 1) * query.pageSize,
        take: query.pageSize,
      }),
      prisma.auditLog.count({ where }),
    ])

    return ok(
      paginate(
        rows.map((r) => ({
          id: r.id,
          actorName: r.actorName,
          action: r.action,
          entity: r.entity,
          entityId: r.entityId,
          ip: r.ip,
          createdAt: r.createdAt.toISOString(),
          metadata: parseJson<Record<string, unknown>>(r.metadata, {}),
        })),
        total,
        query,
      ),
    )
  } catch (error) {
    return handleError(error)
  }
}
