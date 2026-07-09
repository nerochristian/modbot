'use client'

import { Fragment, useEffect, useState } from 'react'
import { SettingsCard } from '@/components/dashboard/setting-section'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/toast'
import { ROLE_LABELS, ROLE_DESCRIPTIONS, type Role } from '@/lib/rbac'

type Group = { label: string; permissions: string[] }
type RolesData = { roles: Role[]; groups: Group[]; matrix: Record<string, string[]> }

const PERMISSION_LABELS: Record<string, string> = {
  'dashboard.view': 'View dashboard',
  'analytics.view': 'View analytics',
  'config.write': 'Customize dashboard',
  'customers.read': 'View customers',
  'customers.write': 'Manage customers',
  'users.read': 'View users',
  'users.write': 'Manage users',
  'users.delete': 'Delete users',
  'reports.read': 'View reports',
  'reports.write': 'Manage reports',
  'billing.read': 'View billing',
  'billing.write': 'Manage billing',
  'notifications.read': 'View notifications',
  'activity.read': 'View activity',
  'audit.read': 'View audit log',
  'settings.read': 'View settings',
  'settings.write': 'Edit settings',
  'admin.access': 'Access admin panel',
  'admin.users.manage': 'Admin: users',
  'admin.roles.manage': 'Admin: roles',
  'admin.features.manage': 'Admin: features',
  'admin.settings.manage': 'Admin: settings',
  'admin.widgets.manage': 'Admin: widgets',
}

export default function RolesAdminPage() {
  const toast = useToast()
  const [data, setData] = useState<RolesData | null>(null)
  const [saving, setSaving] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/admin/roles').then((r) => r.json()).then(setData).catch(() => setData(null))
  }, [])

  async function toggle(role: Role, permission: string, allowed: boolean) {
    if (!data) return
    const key = `${role}:${permission}`
    setSaving(key)
    // optimistic update
    setData((prev) => {
      if (!prev) return prev
      const set = new Set(prev.matrix[role])
      if (allowed) set.add(permission)
      else set.delete(permission)
      return { ...prev, matrix: { ...prev.matrix, [role]: [...set] } }
    })
    try {
      const res = await fetch('/api/admin/roles', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role, permission, allowed }),
      })
      if (!res.ok) throw new Error()
    } catch {
      toast.error('Could not update permission')
      fetch('/api/admin/roles').then((r) => r.json()).then(setData)
    } finally {
      setSaving(null)
    }
  }

  if (!data) {
    return (
      <SettingsCard title="Roles & permissions" description="Control what each role can do.">
        <Skeleton className="h-64 w-full" />
      </SettingsCard>
    )
  }

  return (
    <SettingsCard
      title="Roles & permissions"
      description="Grant or revoke permissions per role. The Admin role always has full access."
    >
      <div className="mb-4 grid grid-cols-3 gap-3">
        {data.roles.map((role) => (
          <div key={role} className="rounded-lg border border-border p-3">
            <p className="text-sm font-semibold capitalize text-foreground">{ROLE_LABELS[role]}</p>
            <p className="mt-0.5 text-xs text-muted">{ROLE_DESCRIPTIONS[role]}</p>
          </div>
        ))}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] text-sm">
          <thead>
            <tr className="border-b border-border text-left">
              <th className="pb-3 font-medium text-muted">Permission</th>
              {data.roles.map((role) => (
                <th key={role} className="pb-3 text-center font-medium capitalize text-muted">
                  {ROLE_LABELS[role]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.groups.map((group) => (
              <Fragment key={group.label}>
                <tr>
                  <td colSpan={4} className="pb-1 pt-4">
                    <Badge tone="neutral">{group.label}</Badge>
                  </td>
                </tr>
                {group.permissions.map((perm) => (
                  <tr key={perm} className="border-b border-border/60">
                    <td className="py-2.5 text-foreground">{PERMISSION_LABELS[perm] ?? perm}</td>
                    {data.roles.map((role) => {
                      const granted = data.matrix[role]?.includes(perm)
                      const locked = role === 'admin'
                      return (
                        <td key={role} className="py-2.5 text-center">
                          <div className="flex justify-center">
                            <Switch
                              checked={locked ? true : !!granted}
                              disabled={locked || saving === `${role}:${perm}`}
                              onChange={(v) => toggle(role, perm, v)}
                              label={`${role} ${perm}`}
                            />
                          </div>
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </SettingsCard>
  )
}
