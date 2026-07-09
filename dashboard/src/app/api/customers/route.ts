import { prisma } from '@/lib/prisma'
import { requireUser, handleError, ok, created, parseListQuery, paginate } from '@/lib/api'
import { customerSchema } from '@/lib/validation'
import { logActivity } from '@/lib/log'
import type { Prisma } from '@prisma/client'

const SORTABLE = new Set(['name', 'mrr', 'createdAt', 'lastActiveAt', 'plan', 'status'])

export async function GET(request: Request) {
  try {
    const guard = await requireUser('customers.read')
    if (guard instanceof Response) return guard

    const url = new URL(request.url)
    const query = parseListQuery(url, { defaultSort: 'mrr', maxPageSize: 100 })

    const where: Prisma.CustomerWhereInput = {}
    if (query.q) {
      where.OR = [
        { name: { contains: query.q } },
        { email: { contains: query.q } },
        { company: { contains: query.q } },
      ]
    }
    if (query.filters.status) where.status = query.filters.status
    if (query.filters.plan) where.plan = query.filters.plan
    if (query.filters.country) where.country = query.filters.country

    const sort = SORTABLE.has(query.sort) ? query.sort : 'mrr'

    const [rows, total, aggregate] = await Promise.all([
      prisma.customer.findMany({
        where,
        orderBy: { [sort]: query.order },
        skip: (query.page - 1) * query.pageSize,
        take: query.pageSize,
      }),
      prisma.customer.count({ where }),
      prisma.customer.aggregate({ where, _sum: { mrr: true } }),
    ])

    return ok({ ...paginate(rows, total, query), totalMrr: aggregate._sum.mrr ?? 0 })
  } catch (error) {
    return handleError(error)
  }
}

export async function POST(request: Request) {
  try {
    const guard = await requireUser('customers.write')
    if (guard instanceof Response) return guard
    const user = guard

    const body = await request.json()
    const data = customerSchema.parse(body)

    const existing = await prisma.customer.findUnique({ where: { email: data.email.toLowerCase() } })
    if (existing) return handleError(new Error('duplicate'))

    const customer = await prisma.customer.create({
      data: {
        name: data.name,
        email: data.email.toLowerCase(),
        company: data.company ?? null,
        plan: data.plan,
        status: data.status,
        country: data.country,
        mrr: data.mrr ?? 0,
      },
    })
    await logActivity({
      userId: user.id,
      actorName: user.name,
      action: 'created_customer',
      target: customer.name,
    })
    return created(customer)
  } catch (error) {
    return handleError(error)
  }
}
