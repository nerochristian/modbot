import { requireUser, handleError, ok } from '@/lib/api'
import { getSelectedGuild } from '@/lib/guild-context'
import { getRealAnalytics } from '@/lib/real-metrics'
import { rangeDays, type DateRange } from '@/lib/dashboard-config'

export async function GET(request: Request) {
  try {
    const guard = await requireUser('analytics.view')
    if (guard instanceof Response) return guard
    const guild = await getSelectedGuild()
    if (!guild) return Response.json({ error: 'Choose a connected server first' }, { status: 409 })

    const requestedRange = new URL(request.url).searchParams.get('range')
    const range: DateRange = ['7d', '30d', '90d', '12m'].includes(requestedRange ?? '')
      ? requestedRange as DateRange
      : '30d'
    const data = await getRealAnalytics(guild, rangeDays(range))
    return ok({ range, ...data })
  } catch (error) {
    return handleError(error)
  }
}
