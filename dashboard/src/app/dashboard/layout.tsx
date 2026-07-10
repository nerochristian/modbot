import { redirect } from 'next/navigation'
import { cookies } from 'next/headers'
import { getCurrentUser } from '@/lib/session'
import { prisma } from '@/lib/prisma'
import { mergeConfig, type DashboardConfig } from '@/lib/dashboard-config'
import { parseJson } from '@/lib/json'
import { ConfigProvider } from '@/components/providers/config-provider'
import { DashboardShell } from '@/components/dashboard/shell'
import type { SessionUser } from '@/lib/store'
import { getManageableGuilds } from '@/lib/discord'
import { SELECTED_GUILD_COOKIE } from '@/lib/guild-context'

  const user = await getCurrentUser()
  if (!user) redirect('/login')
  const guilds = await getManageableGuilds(user.id)
  const selectedId = (await cookies()).get(SELECTED_GUILD_COOKIE)?.value
  const currentGuild = guilds.find((guild) => guild.id === selectedId && guild.installed)
  if (!currentGuild) redirect('/servers')

  const configRow = await prisma.dashboardConfig.findUnique({ where: { userId: user.id } })
  const config = mergeConfig(
    configRow ? parseJson<Partial<DashboardConfig>>(configRow.config, {}) : null,
  )

  const sessionUser: SessionUser = {
    id: user.id,
    name: user.name,
    email: user.email,
    role: user.role,
    avatarColor: user.avatarColor,
    title: user.title,
    permissions: user.permissions,
  }

  return (
    <ConfigProvider config={config} user={sessionUser}>
      <DashboardShell permissions={user.permissions} guilds={guilds} currentGuild={currentGuild}>
        {children}
      </DashboardShell>
    </ConfigProvider>
  )
}
  const user = await getCurrentUser()
  if (!user) redirect('/login')

  const configRow = await prisma.dashboardConfig.findUnique({ where: { userId: user.id } })
  const config = mergeConfig(
    configRow ? parseJson<Partial<DashboardConfig>>(configRow.config, {}) : null,
  )

  const sessionUser: SessionUser = {
    id: user.id,
    name: user.name,
    email: user.email,
    role: user.role,
    avatarColor: user.avatarColor,
    title: user.title,
    permissions: user.permissions,
  }

  return (
    <ConfigProvider config={config} user={sessionUser}>
      <DashboardShell permissions={user.permissions}>{children}</DashboardShell>
    </ConfigProvider>
  )
}
