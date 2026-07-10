import { getCurrentUser } from '@/lib/session'
import { getManageableGuilds, DiscordReauthRequiredError } from '@/lib/discord'
import { handleError, ok } from '@/lib/api'

export async function GET(request: Request) {
  const user = await getCurrentUser()
  if (!user) return Response.json({ error: 'Unauthorized' }, { status: 401 })
  try {
    const force = new URL(request.url).searchParams.get('refresh') === '1'
    return ok({ guilds: await getManageableGuilds(user.id, force) })
  } catch (error) {
    if (error instanceof DiscordReauthRequiredError) {
      return Response.json({ error: error.message, reauthorize: true }, { status: 401 })
    }
    return handleError(error)
  }
}
