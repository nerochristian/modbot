import { cookies } from 'next/headers'
import { getManageableGuilds } from '@/lib/discord'
import { SELECTED_GUILD_COOKIE } from '@/lib/guild-context'
import { handleError, ok, requireMutation } from '@/lib/api'
import { secureCookies } from '@/lib/auth'

export async function POST(request: Request) {
  const guard = await requireMutation(request)
  if (guard instanceof Response) return guard
  const user = guard
  try {
    const body = (await request.json()) as { guildId?: unknown }
    const guildId = typeof body.guildId === 'string' ? body.guildId : ''
    if (!/^\d{15,22}$/.test(guildId)) {
      return Response.json({ error: 'Invalid server ID' }, { status: 400 })
    }
    const guilds = await getManageableGuilds(user.id, true)
    const guild = guilds.find((item) => item.id === guildId)
    if (!guild) return Response.json({ error: 'You are not authorized for this server' }, { status: 403 })
    if (!guild.installed) return Response.json({ error: 'Add Docket to this server first' }, { status: 409 })

    const cookieStore = await cookies()
    cookieStore.set(SELECTED_GUILD_COOKIE, guild.id, {
      httpOnly: true,
      sameSite: 'lax',
      secure: secureCookies(),
      path: '/',
      maxAge: 60 * 60 * 24 * 30,
      priority: 'high',
    })
    return ok({ guild })
  } catch (error) {
    return handleError(error)
  }
}
