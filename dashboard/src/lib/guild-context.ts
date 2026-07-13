import 'server-only'

import { getCurrentUser } from '@/lib/session'
import { getManageableGuilds, type ManagedGuild } from '@/lib/discord'

export { SELECTED_GUILD_COOKIE } from '@/lib/auth'

export async function getSelectedGuild(): Promise<ManagedGuild | null> {
  const user = await getCurrentUser()
  if (!user?.selectedGuildId) return null
  const guilds = await getManageableGuilds(user.id)
  return guilds.find((guild) => guild.id === user.selectedGuildId && guild.installed) ?? null
}

export async function getGuildsForCurrentUser(force = false): Promise<ManagedGuild[]> {
  const user = await getCurrentUser()
  if (!user) return []
  return getManageableGuilds(user.id, force)
}
