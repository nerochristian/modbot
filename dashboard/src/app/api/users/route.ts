import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok, created, apiError, parseListQuery, paginate } from '@/lib/api'
import { createUserSchema } from '@/lib/validation'
import { hashPassword } from '@/lib/auth'
import { logActivity, logAudit, notify } from '@/lib/log'
import { DEFAULT_DASHBOARD_CONFIG } from '@/lib/dashboard-config'
import type { Prisma } from '@prisma/client'

const SORTABLE = new Set(['name', 'email', 'role', 'status', 'createdAt', 'lastLoginAt'])

export async function GET(request: Request) {
  try {
    const guard = await requireUser('users.read')
    if (guard instanceof Response) return guard

    const url = new URL(request.url)
    const query = parseListQuery(url, { defaultSort: 'createdAt' })

    const where: Prisma.UserWhereInput = {}
    if (query.q) {
      where.OR = [{ name: { contains: query.q } }, { email: { contains: query.q } }]
    }
    if (query.filters.role) where.role = query.filters.role
    if (query.filters.status) where.status = query.filters.status

    const sort = SORTABLE.has(query.sort) ? query.sort : 'createdAt'

    const [rows, total] = await Promise.all([
      prisma.user.findMany({
        where,
        orderBy: { [sort]: query.order },
        skip: (query.page - 1) * query.pageSize,
        take: query.pageSize,
        select: {
          id: true,
          name: true,
          email: true,
          role: true,
          status: true,
          title: true,
          avatarColor: true,
          createdAt: true,
          lastLoginAt: true,
        },
      }),
      prisma.user.count({ where }),
    ])

    return ok(paginate(rows, total, query))
  } catch (error) {
    return handleError(error)
  }
}

export async function POST(request: Request) {
  try {
    const guard = await requireUser('users.write')
    if (guard instanceof Response) return guard
    const actor = guard

    const body = await request.json()
    const data = createUserSchema.parse(body)

    // Privilege-escalation guard: only an admin may create an admin account.
    // `users.write` is granted to managers, so without this a non-admin could
    // mint an admin and escalate. Role removal is guarded elsewhere; this
    // guards role *granting*.
    if (data.role === 'admin' && actor.role !== 'admin') {
      return apiError('Only an admin can create an admin account.', 403)
    }

    const existing = await prisma.user.findUnique({ where: { email: data.email.toLowerCase() } })
    if (existing) return apiError('A user with that email already exists.', 409)

    const password = data.password ?? crypto.randomUUID()
    const user = await prisma.user.create({
      data: {
        name: data.name,
        email: data.email.toLowerCase(),
        role: data.role,
        status: data.password ? 'active' : 'invited',
        passwordHash: await hashPassword(password),
        dashboardConfig: { create: { config: JSON.stringify(DEFAULT_DASHBOARD_CONFIG) } },
      },
    })

    await logActivity({ userId: actor.id, actorName: actor.name, action: 'invited_user', target: user.name })
    await logAudit({ userId: actor.id, actorName: actor.name, action: 'user.create', entity: 'User', entityId: user.id })
    await notify({
      userId: user.id,
      type: 'system',
      title: 'Welcome to Docket',
      body: 'Your account has been created. Explore your dashboard to get started.',
      href: '/dashboard',
    })

    return created({ id: user.id, name: user.name, email: user.email, role: user.role, status: user.status })
  } catch (error) {
    return handleError(error)
  }
}
