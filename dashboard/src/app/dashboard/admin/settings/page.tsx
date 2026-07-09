'use client'

import { useEffect, useState } from 'react'
import { SettingsCard, SettingRow } from '@/components/dashboard/setting-section'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/toast'
import { ROLES, ROLE_LABELS } from '@/lib/rbac'

type Settings = Record<string, unknown>

export default function GlobalSettingsAdminPage() {
  const toast = useToast()
  const [settings, setSettings] = useState<Settings | null>(null)
  const [savingText, setSavingText] = useState(false)

  useEffect(() => {
    fetch('/api/admin/settings').then((r) => r.json()).then((d) => setSettings(d.settings)).catch(() => setSettings({}))
  }, [])

  async function save(key: string, value: unknown) {
    setSettings((prev) => ({ ...(prev ?? {}), [key]: value }))
    try {
      const res = await fetch('/api/admin/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value }),
      })
      if (!res.ok) throw new Error()
    } catch {
      toast.error('Could not save setting')
    }
  }

  async function saveText() {
    setSavingText(true)
    await Promise.all([
      save('app.name', settings?.['app.name'] ?? 'Nebula'),
      save('app.supportEmail', settings?.['app.supportEmail'] ?? ''),
    ])
    setSavingText(false)
    toast.success('Settings saved')
  }

  if (!settings) {
    return (
      <SettingsCard title="Global settings" description="Workspace-wide configuration.">
        <Skeleton className="h-64 w-full" />
      </SettingsCard>
    )
  }

  const get = <T,>(key: string, fallback: T) => (settings[key] as T) ?? fallback

  return (
    <>
      <SettingsCard
        title="General"
        description="Basic information about your workspace."
        footer={
          <Button onClick={saveText} loading={savingText}>
            Save changes
          </Button>
        }
      >
        <div className="divide-y divide-border">
          <SettingRow label="Application name" description="Shown in the UI and emails.">
            <Input
              className="w-56"
              value={get('app.name', 'Aegis')}
              onChange={(e) => setSettings({ ...settings, 'app.name': e.target.value })}
            />
          </SettingRow>
          <SettingRow label="Support email" description="Where support requests are sent.">
            <Input
              className="w-56"
              value={get('app.supportEmail', '')}
              onChange={(e) => setSettings({ ...settings, 'app.supportEmail': e.target.value })}
            />
          </SettingRow>
          <SettingRow label="Default role" description="Assigned to new sign-ups.">
            <Select
              className="w-44"
              options={ROLES.map((r) => ({ label: ROLE_LABELS[r], value: r }))}
              value={get('app.defaultRole', 'viewer')}
              onChange={(e) => save('app.defaultRole', e.target.value)}
            />
          </SettingRow>
        </div>
      </SettingsCard>

      <SettingsCard title="Access & security" description="Control sign-ups and security policy.">
        <div className="divide-y divide-border">
          <SettingRow label="Allow sign-ups" description="Let new users create accounts.">
            <Switch checked={get('app.signupsEnabled', true)} onChange={(v) => save('app.signupsEnabled', v)} label="Allow sign-ups" />
          </SettingRow>
          <SettingRow label="Enforce two-factor" description="Require 2FA for all members.">
            <Switch checked={get('security.enforce2fa', false)} onChange={(v) => save('security.enforce2fa', v)} label="Enforce 2FA" />
          </SettingRow>
          <SettingRow label="Maintenance mode" description="Temporarily restrict access to admins.">
            <Switch checked={get('app.maintenanceMode', false)} onChange={(v) => save('app.maintenanceMode', v)} label="Maintenance mode" />
          </SettingRow>
        </div>
      </SettingsCard>
    </>
  )
}
