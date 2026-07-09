import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok, created, apiError, parseListQuery, paginate } from '@/lib/api'
import { caseSchema } from '@/lib/validation'
import { logActivity } from '@/lib/log'
import type { Prisma } from '@prisma/client'

const SORTABLE = new Set(['ref', 'type', 'severity', 'status', 'createdAt', 'expiresAt'])

export async function GET(request: Request) {
  try {
    const guard = await requireUser('cases.read')
    if (guard instanceof Response) return guard

    const url = new URL(request.url)
    const query = parseListQuery(url, { defaultSort: 'createdAt', maxPageSize: 100 })

    const where: Prisma.CaseWhereInput = {}
    if (query.q) {
      const or: Prisma.CaseWhereInput[] = [{ reason: { contains: query.q } }]
      if (/^\d+$/.test(query.q)) or.push({ ref: Number(query.q) })
      where.OR = or
    }
    if (query.filters.type) where.type = query.filters.type
    if (query.filters.severity) where.severity = query.filters.severity
    if (query.filters.status) where.status = query.filters.status
    const memberId = query.filters.memberId || url.searchParams.get('member') || ''
    if (memberId) where.memberId = memberId

    const sort = SORTABLE.has(query.sort) ? query.sort : 'createdAt'

    const [rows, total, open] = await Promise.all([
      prisma.case.findMany({
        where,
        orderBy: { [sort]: query.order },
        skip: (query.page - 1) * query.pageSize,
        take: query.pageSize,
        include: {
          member: {
            select: { id: true, username: true, displayName: true, discordId: true, avatarColor: true },
          },
        },
      }),
      prisma.case.count({ where }),
      prisma.case.count({ where: { ...where, status: 'open' } }),
    ])

    return ok({ ...paginate(rows, total, query), open })
  } catch (error) {
    return handleError(error)
  }
}

export async function POST(request: Request) {
  try {
    const guard = await requireUser('cases.write')
    if (guard instanceof Response) return guard
    const user = guard

    const body = await request.json()
    const data = caseSchema.parse(body)

    const member = await prisma.member.findUnique({ where: { id: data.memberId } })
    if (!member) return apiError('Member not found', 404)

    const top = await prisma.case.findFirst({ orderBy: { ref: 'desc' }, select: { ref: true } })
    const ref = (top?.ref ?? 1000) + 1

    const hours = data.durationHours ?? 0
    const expiresAt = hours > 0 ? new Date(Date.now() + hours * 3600_000) : null

    const caseRow = await prisma.case.create({
      data: {
        ref,
        memberId: data.memberId,
        type: data.type,
        severity: data.severity,
        status: 'open',
        reason: data.reason,
        moderator: user.name,
        moderatorId: user.id,
        channel: data.channel ?? null,
        expiresAt,
      },
    })

    if (data.type === 'warn') {
      await prisma.member.update({
        where: { id: member.id },
        data: { warnings: { increment: 1 } },
      })
    } else if (['mute', 'timeout', 'kick', 'ban'].includes(data.type)) {
      const standing = data.type === 'ban' ? 'banned' : data.type === 'mute' || data.type === 'timeout' ? 'muted' : member.standing
      if (standing !== member.standing) {
        await prisma.member.update({ where: { id: member.id }, data: { standing } })
      }
    }

    await logActivity({
      userId: user.id,
      actorName: user.name,
      action: 'created_case',
      target: `#CASE-${String(ref).padStart(4, '0')}`,
    })
    return created(caseRow)
  } catch (error) {
    return handleError(error)
  }
}
