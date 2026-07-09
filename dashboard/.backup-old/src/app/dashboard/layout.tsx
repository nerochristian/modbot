import { redirect } from 'next/navigation'
import { getCurrentUser } from '@/lib/session'
import { prisma } from '@/lib/prisma'
import { mergeConfig, type DashboardConfig } from '@/lib/dashboard-config'
import { parseJson } from '@/lib/json'
import { ConfigProvider } from '@/components/providers/config-provider'
import { DashboardShell } from '@/components/dashboard/shell'
import type { SessionUser } from '@/lib/store'

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
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
