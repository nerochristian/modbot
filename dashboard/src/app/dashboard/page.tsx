import type { Metadata } from 'next'
import { redirect } from 'next/navigation'
import { OverviewClient } from '@/components/dashboard/overview-client'
import { getSelectedGuild } from '@/lib/guild-context'
import { prisma } from '@/lib/prisma'

export const metadata: Metadata = { title: 'Overview' }

export default async function DashboardPage() {
  const guild = await getSelectedGuild()
  if (!guild) redirect('/servers')

  const [dashboardAdministrators, auditEvents] = await Promise.all([
    prisma.guildMembership.count({
      where: { guildId: guild.id, role: 'admin', source: 'discord', status: 'active' },
    }),
    prisma.auditLog.count({ where: { guildId: guild.id } }),
  ])

  return (
    <OverviewClient
      workspaceSummary={{
        dashboardAdministrators,
        auditEvents,
        serverMembers: guild.memberCount,
      }}
    />
  )
}
