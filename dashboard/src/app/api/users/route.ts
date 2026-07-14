import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok, parseListQuery, paginate } from '@/lib/api'
import { discordAvatarUrl } from '@/lib/discord'
import type { Prisma } from '@prisma/client'

const SORTABLE = new Set(['name', 'email', 'createdAt', 'lastLoginAt'])

function presentMembership(row: {
  role: string
  status: string
  createdAt: Date
  user: {
    id: string
    name: string
    email: string
    title: string | null
    avatarColor: string
    discordId: string | null
    discordAvatar: string | null
    lastLoginAt: Date | null
  }
}) {
  return {
    id: row.user.id,
    name: row.user.name,
    email: row.user.email,
    title: row.user.title,
    avatarColor: row.user.avatarColor,
    avatarUrl: row.user.discordId
      ? discordAvatarUrl({ id: row.user.discordId, avatar: row.user.discordAvatar })
      : null,
    lastLoginAt: row.user.lastLoginAt,
    role: row.role,
    status: row.status === 'revoked' ? 'suspended' : row.status,
    createdAt: row.createdAt,
  }
}

export async function GET(request: Request) {
  try {
    const guard = await requireUser('users.read')
    if (guard instanceof Response) return guard
    const guildId = guard.selectedGuildId as string
    const query = parseListQuery(new URL(request.url), { defaultSort: 'createdAt' })
    const where: Prisma.GuildMembershipWhereInput = {
      guildId,
      role: 'admin',
      source: 'discord',
      status: 'active',
    }
    if (query.q) {
      where.user = {
        OR: [{ name: { contains: query.q } }, { email: { contains: query.q } }],
      }
    }
    const sort = SORTABLE.has(query.sort) ? query.sort : 'createdAt'
    const orderBy: Prisma.GuildMembershipOrderByWithRelationInput =
      sort === 'createdAt'
        ? { [sort]: query.order }
        : { user: { [sort]: query.order } }
    const [rows, total] = await Promise.all([
      prisma.guildMembership.findMany({
        where,
        orderBy,
        skip: (query.page - 1) * query.pageSize,
        take: query.pageSize,
        include: {
          user: {
            select: {
              id: true,
              name: true,
              email: true,
              title: true,
              avatarColor: true,
              discordId: true,
              discordAvatar: true,
              lastLoginAt: true,
            },
          },
        },
      }),
      prisma.guildMembership.count({ where }),
    ])
    return ok(paginate(rows.map(presentMembership), total, query))
  } catch (error) {
    return handleError(error)
  }
}
