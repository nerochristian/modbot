import 'server-only'

import { cookies } from 'next/headers'
import { SELECTED_GUILD_COOKIE } from '@/lib/auth'
import { getCurrentUser } from '@/lib/session'
import { getManageableGuilds, type ManagedGuild } from '@/lib/discord'

export { SELECTED_GUILD_COOKIE } from '@/lib/auth'

export async function getSelectedGuild(): Promise<ManagedGuild | null> {
  const user = await getCurrentUser()
  if (!user) return null
  const selectedId = (await cookies()).get(SELECTED_GUILD_COOKIE)?.value
  if (!selectedId) return null
  const guilds = await getManageableGuilds(user.id)
  return guilds.find((guild) => guild.id === selectedId && guild.installed) ?? null
}

export async function getGuildsForCurrentUser(force = false): Promise<ManagedGuild[]> {
  const user = await getCurrentUser()
  if (!user) return []
  return getManageableGuilds(user.id, force)
}
