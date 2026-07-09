'use client'

import { useEffect, useState } from 'react'
import { SettingsCard } from '@/components/dashboard/setting-section'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/toast'

type Feature = { key: string; name: string; description: string; enabled: boolean; rolloutRole: string }

export default function FeaturesAdminPage() {
  const toast = useToast()
  const [features, setFeatures] = useState<Feature[] | null>(null)

  useEffect(() => {
    fetch('/api/admin/features').then((r) => r.json()).then((d) => setFeatures(d.features)).catch(() => setFeatures([]))
  }, [])

  async function toggle(key: string, enabled: boolean) {
    setFeatures((prev) => prev?.map((f) => (f.key === key ? { ...f, enabled } : f)) ?? null)
    try {
      const res = await fetch('/api/admin/features', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, enabled }),
      })
      if (!res.ok) throw new Error()
      toast.success(`${enabled ? 'Enabled' : 'Disabled'} feature`)
    } catch {
      toast.error('Could not update feature')
      fetch('/api/admin/features').then((r) => r.json()).then((d) => setFeatures(d.features))
    }
  }

  return (
    <SettingsCard title="Feature flags" description="Roll features out or back across the entire workspace.">
      {!features ? (
        <Skeleton className="h-48 w-full" />
      ) : (
        <div className="divide-y divide-border">
          {features.map((f) => (
            <div key={f.key} className="flex items-center justify-between gap-4 py-4 first:pt-0 last:pb-0">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-foreground">{f.name}</p>
                  <Badge tone={f.enabled ? 'success' : 'neutral'}>{f.enabled ? 'On' : 'Off'}</Badge>
                  {f.rolloutRole !== 'all' && <Badge tone="info">{f.rolloutRole} only</Badge>}
                </div>
                <p className="mt-0.5 text-sm text-muted">{f.description}</p>
                <code className="text-xs text-muted-2">{f.key}</code>
              </div>
              <Switch checked={f.enabled} onChange={(v) => toggle(f.key, v)} label={`Toggle ${f.name}`} />
            </div>
          ))}
        </div>
      )}
    </SettingsCard>
  )
}
