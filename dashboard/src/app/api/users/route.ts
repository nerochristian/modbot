import { prisma } from '@/lib/prisma'
import { requireMutation, requireUser, handleError, ok, created, apiError, parseListQuery, paginate } from '@/lib/api'
import { createUserSchema } from '@/lib/validation'
import { hashPassword } from '@/lib/auth'
import { invalidateGuildCache } from '@/lib/discord'
import { logActivity, logAudit, notify } from '@/lib/log'
import { DEFAULT_DASHBOARD_CONFIG } from '@/lib/dashboard-config'
import type { Prisma } from '@prisma/client'

const SORTABLE = new Set(['name', 'email', 'role', 'status', 'createdAt', 'lastLoginAt'])

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
    lastLoginAt: Date | null
  }
}) {
  return {
    ...row.user,
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
    const where: Prisma.GuildMembershipWhereInput = { guildId }
    if (query.q) {
      where.user = {
        OR: [{ name: { contains: query.q } }, { email: { contains: query.q } }],
      }
    }
    if (query.filters.role) where.role = query.filters.role
    if (query.filters.status) {
      where.status = query.filters.status === 'suspended' ? 'revoked' : query.filters.status
    }
    const sort = SORTABLE.has(query.sort) ? query.sort : 'createdAt'
    const orderBy: Prisma.GuildMembershipOrderByWithRelationInput =
      sort === 'role' || sort === 'status' || sort === 'createdAt'
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

export async function POST(request: Request) {
  try {
    const guard = await requireMutation(request, 'users.write')
    if (guard instanceof Response) return guard
    const guildId = guard.selectedGuildId as string
    const data = createUserSchema.parse(await request.json())
    if (data.password) return apiError('Password accounts are disabled; invite by Discord email instead.', 422)
    if (data.role === 'admin' && guard.role !== 'admin') {
      return apiError('Only a workspace admin can invite another admin.', 403)
    }

    const email = data.email.toLowerCase()
    let user = await prisma.user.findUnique({ where: { email } })
    if (user?.status === 'suspended') {
      return apiError('This identity is suspended and cannot be invited.', 409)
    }
    if (!user) {
      user = await prisma.user.create({
        data: {
          name: data.name,
          email,
          role: 'viewer',
          status: 'invited',
          passwordHash: await hashPassword(crypto.randomUUID()),
          dashboardConfig: { create: { config: JSON.stringify(DEFAULT_DASHBOARD_CONFIG) } },
        },
      })
    } else if (!user.discordId && user.status !== 'suspended' && user.status !== 'invited') {
      user = await prisma.user.update({ where: { id: user.id }, data: { status: 'invited' } })
    }
    const existing = await prisma.guildMembership.findUnique({
      where: { guildId_userId: { guildId, userId: user.id } },
    })
    if (existing && existing.status !== 'revoked') {
      return apiError('This user already belongs to the server workspace.', 409)
    }
    const membership = await prisma.guildMembership.upsert({
      where: { guildId_userId: { guildId, userId: user.id } },
      create: { guildId, userId: user.id, role: data.role, status: 'invited', source: 'invite' },
      update: { role: data.role, status: 'invited', source: 'invite', verifiedAt: null },
    })
    invalidateGuildCache(user.id)

    await logActivity({ guildId, userId: guard.id, actorName: guard.name, action: 'invited_user', target: user.name })
    await logAudit({ guildId, userId: guard.id, actorName: guard.name, action: 'membership.invite', entity: 'GuildMembership', entityId: membership.id })
    await notify({
      guildId,
      userId: user.id,
      type: 'system',
      title: 'Server workspace invitation',
      body: 'Sign in with your verified Discord account to accept this server workspace invitation.',
      href: '/servers',
    })

    return created({ id: user.id, name: user.name, email: user.email, role: membership.role, status: membership.status })
  } catch (error) {
    return handleError(error)
  }
}
