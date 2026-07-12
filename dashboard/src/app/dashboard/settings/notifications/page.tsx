'use client'

import { SettingsCard } from '@/components/dashboard/setting-section'
import { Switch } from '@/components/ui/switch'
import { useConfigStore } from '@/lib/store'
const GROUPS = [
  { key: 'product' as const, label: 'Team announcements', description: 'In-app broadcasts sent by this server\'s dashboard administrators.' },
  { key: 'mentions' as const, label: 'Mentions & shared activity', description: 'In-app notifications when a teammate needs your attention.' },
]

export default function NotificationSettingsPage() {
  const notifications = useConfigStore((s) => s.config.notifications)
  const setPref = useConfigStore((s) => s.setNotificationPref)

  return (
    <SettingsCard
      title="Notifications"
      description="Choose which in-app updates appear in your notification center. Preferences save automatically."
    >
      <div className="divide-y divide-border">
        {GROUPS.map((group) => (
          <div key={group.key} className="flex items-center justify-between gap-6 py-4 first:pt-0 last:pb-0">
            <div>
              <p className="font-medium text-foreground">{group.label}</p>
              <p className="mt-0.5 text-xs text-muted">{group.description}</p>
            </div>
            <Switch
              checked={notifications[group.key].inApp}
              onChange={(enabled) => setPref(group.key, 'inApp', enabled)}
              label={`Toggle ${group.label}`}
            />
          </div>
        ))}
      </div>
    </SettingsCard>
  )
}
