import { prisma } from '@/lib/prisma'
import { requireMutation, requireUser, handleError, ok, created } from '@/lib/api'
import { savedViewSchema } from '@/lib/validation'

export async function GET(request: Request) {
  try {
    const guard = await requireUser('dashboard.view')
    if (guard instanceof Response) return guard
    const user = guard

    const url = new URL(request.url)
    const page = url.searchParams.get('page') ?? undefined

    const views = await prisma.savedView.findMany({
      where: { userId: user.id, guildId: user.selectedGuildId as string, ...(page ? { page } : {}) },
      orderBy: { createdAt: 'desc' },
    })
    return ok({ views })
  } catch (error) {
    return handleError(error)
  }
}

export async function POST(request: Request) {
  try {
    const guard = await requireMutation(request, 'dashboard.view')
    if (guard instanceof Response) return guard
    const user = guard

    const body = await request.json()
    const data = savedViewSchema.parse(body)

    const view = await prisma.savedView.create({
      data: {
        userId: user.id,
        guildId: user.selectedGuildId as string,
        name: data.name,
        page: data.page,
        state: JSON.stringify(data.state),
      },
    })
    return created(view)
  } catch (error) {
    return handleError(error)
  }
}
