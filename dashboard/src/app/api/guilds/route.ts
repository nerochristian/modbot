import { NextResponse } from 'next/server'
import { getCurrentUser } from '@/lib/session'
import { prisma } from '@/lib/prisma'
import { apiError } from '@/lib/api'

/**
 * GET /api/guilds
 * Returns the authenticated user's Discord guilds with bot presence info.
 * Uses the stored Discord access token from the User record.
 */
export async function GET() {
  const user = await getCurrentUser()
  if (!user) return apiError('Unauthorized', 401)

  const dbUser = await prisma.user.findUnique({
    where: { id: user.id },
    select: {
      discordId: true,
      discordAccessToken: true,
      discordRefreshToken: true,
      discordTokenExpiresAt: true,
    },
  })

  if (!dbUser?.discordAccessToken) {
    return apiError('No Discord token stored. Please re-login.', 401)
  }

  // Fetch guilds from Discord
  const guildsRes = await fetch('https://discord.com/api/users/@me/guilds', {
    headers: { Authorization: `Bearer ${dbUser.discordAccessToken}` },
  })

  if (!guildsRes.ok) {
    // Token likely expired — in production you would refresh here
    return apiError('Failed to fetch guilds from Discord', 502)
  }

  const guilds: Array<{
    id: string
    name: string
    icon: string | null
    owner: boolean
    permissions: string
    approximate_member_count?: number
  }> = await guildsRes.json()

  // Check which guilds the bot is in by querying the real modbot database
  // We connect directly to the SQLite/Postgres used by the bot (same DATABASE_URL or modbot.db)
  let botGuildIds = new Set<string>()
  try {
    // For production the bot uses the same DATABASE_URL.
    // Here we do a lightweight check via raw query if possible, or fall back to a simple presence list.
    // Since the dashboard Prisma may point to a different DB, we use the bot's database path when available.
    const botDbUrl = process.env.DATABASE_URL || 'file:../modbot.db'

    // Simple approach: if using SQLite file, we can read it.
    // For Postgres we assume the dashboard DB and bot DB are the same (recommended setup).
    // In this implementation we assume the Prisma client can reach the guild_settings table.
    const botGuilds = await prisma.$queryRawUnsafe<{ guild_id: string }[]>(
      `SELECT DISTINCT guild_id FROM guild_settings`
    ).catch(() => [])

    botGuildIds = new Set(botGuilds.map((g) => g.guild_id))
  } catch {
    // If the query fails we still return the list without bot presence (graceful)
  }

  const result = guilds
    .filter((g) => {
      // Only show guilds where user has admin or is owner (permission bit 0x8 = ADMINISTRATOR)
      const perms = BigInt(g.permissions)
      const hasAdmin = (perms & 0x8n) === 0x8n || g.owner
      return hasAdmin
    })
    .map((g) => ({
      id: g.id,
      name: g.name,
      icon: g.icon
        ? `https://cdn.discordapp.com/icons/${g.id}/${g.icon}.png?size=128`
        : null,
      memberCount: g.approximate_member_count ?? null,
      botInGuild: botGuildIds.has(g.id),
      isOwner: g.owner,
    }))
    .sort((a, b) => (b.memberCount ?? 0) - (a.memberCount ?? 0))

  return NextResponse.json(result)
}
