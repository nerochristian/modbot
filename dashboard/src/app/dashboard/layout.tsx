import { redirect } from 'next/navigation'
import { ConfigProvider } from '@/components/providers/config-provider'
import { DashboardShell } from '@/components/dashboard/shell'
import { mergeConfig, type DashboardConfig } from '@/lib/dashboard-config'
import { getManageableGuilds } from '@/lib/discord'
import { parseJson } from '@/lib/json'
import { prisma } from '@/lib/prisma'
import { getCurrentUser } from '@/lib/session'
import type { SessionUser } from '@/lib/store'

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser()
  if (!user) redirect('/login')

  const guilds = await getManageableGuilds(user.id)
  const currentGuild = guilds.find((guild) => guild.id === user.selectedGuildId && guild.installed)
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
