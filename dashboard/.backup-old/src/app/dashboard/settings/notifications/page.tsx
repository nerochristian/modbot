'use client'

import { SettingsCard } from '@/components/dashboard/setting-section'
import { Switch } from '@/components/ui/switch'
import { useConfigStore } from '@/lib/store'
import type { DashboardConfig } from '@/lib/dashboard-config'

const GROUPS: { key: keyof DashboardConfig['notifications']; label: string; description: string }[] = [
  { key: 'billing', label: 'Billing & payments', description: 'Invoices, payment receipts, and failures.' },
  { key: 'security', label: 'Security', description: 'New sign-ins, password changes, and 2FA.' },
  { key: 'product', label: 'Product updates', description: 'New features, changelog, and announcements.' },
  { key: 'mentions', label: 'Mentions & activity', description: 'When someone mentions you or shares a view.' },
]

const CHANNELS: { key: 'email' | 'push' | 'inApp'; label: string }[] = [
  { key: 'email', label: 'Email' },
  { key: 'push', label: 'Push' },
  { key: 'inApp', label: 'In-app' },
]

export default function NotificationSettingsPage() {
  const notifications = useConfigStore((s) => s.config.notifications)
  const setPref = useConfigStore((s) => s.setNotificationPref)

  return (
    <SettingsCard
      title="Notifications"
      description="Choose how you want to be notified. Preferences save automatically."
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left">
              <th className="pb-3 font-medium text-muted">Category</th>
              {CHANNELS.map((c) => (
                <th key={c.key} className="pb-3 text-center font-medium text-muted">
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {GROUPS.map((g) => (
              <tr key={g.key}>
                <td className="py-4 pr-4">
                  <p className="font-medium text-foreground">{g.label}</p>
                  <p className="text-xs text-muted">{g.description}</p>
                </td>
                {CHANNELS.map((c) => (
                  <td key={c.key} className="py-4 text-center">
                    <div className="flex justify-center">
                      <Switch
                        checked={notifications[g.key][c.key]}
                        onChange={(v) => setPref(g.key, c.key, v)}
                        label={`${g.label} ${c.label}`}
                      />
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SettingsCard>
  )
}
