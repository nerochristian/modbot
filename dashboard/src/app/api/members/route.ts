import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok, created, parseListQuery, paginate } from '@/lib/api'
import { memberSchema } from '@/lib/validation'
import { logActivity } from '@/lib/log'
import type { Prisma } from '@prisma/client'

const SORTABLE = new Set(['username', 'displayName', 'warnings', 'messages', 'joinedAt', 'lastActiveAt', 'standing', 'riskLevel'])

const AVATAR_COLORS = ['#5865f2', '#3ddc97', '#f5a524', '#f0476b', '#38bdf8', '#8b5cf6', '#fb923c']

export async function GET(request: Request) {
  try {
    const guard = await requireUser('members.read')
    if (guard instanceof Response) return guard

    const url = new URL(request.url)
    const query = parseListQuery(url, { defaultSort: 'joinedAt', maxPageSize: 100 })

    const where: Prisma.MemberWhereInput = {}
    if (query.q) {
      where.OR = [
        { username: { contains: query.q } },
        { displayName: { contains: query.q } },
        { discordId: { contains: query.q } },
      ]
    }
    if (query.filters.standing) where.standing = query.filters.standing
    if (query.filters.riskLevel) where.riskLevel = query.filters.riskLevel

    const sort = SORTABLE.has(query.sort) ? query.sort : 'joinedAt'

    const [rows, total, flagged] = await Promise.all([
      prisma.member.findMany({
        where,
        orderBy: { [sort]: query.order },
        skip: (query.page - 1) * query.pageSize,
        take: query.pageSize,
      }),
      prisma.member.count({ where }),
      prisma.member.count({ where: { ...where, standing: { in: ['watchlist', 'muted', 'banned'] } } }),
    ])

    return ok({ ...paginate(rows, total, query), flagged })
  } catch (error) {
    return handleError(error)
  }
}

export async function POST(request: Request) {
  try {
    const guard = await requireUser('members.write')
    if (guard instanceof Response) return guard
    const user = guard

    const body = await request.json()
    const data = memberSchema.parse(body)

    const existing = await prisma.member.findUnique({ where: { discordId: data.discordId } })
    if (existing) return handleError(new Error('duplicate'))

    const member = await prisma.member.create({
      data: {
        username: data.username,
        displayName: data.displayName,
        discordId: data.discordId,
        standing: data.standing,
        riskLevel: data.riskLevel,
        note: data.note ?? null,
        avatarColor: AVATAR_COLORS[Math.abs(hash(data.discordId)) % AVATAR_COLORS.length],
      },
    })
    await logActivity({
      userId: user.id,
      actorName: user.name,
      action: 'added_member',
      target: member.displayName,
    })
    return created(member)
  } catch (error) {
    return handleError(error)
  }
}

function hash(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h << 5) - h + s.charCodeAt(i)
  return h
}
