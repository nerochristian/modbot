'use client'

import { useEffect, useState } from 'react'
import { SettingsCard } from '@/components/dashboard/setting-section'
import { Field, Input, Textarea } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Avatar } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorState } from '@/components/ui/empty-state'
import { useToast } from '@/components/ui/toast'
import { useConfigStore } from '@/lib/store'
import { ACCENT_COLORS } from '@/lib/dashboard-config'
import { ROLE_LABELS, type Role } from '@/lib/rbac'
import { cn } from '@/lib/utils'

type Profile = {
  name: string
  email: string
  role: string
  title: string | null
  phone: string | null
  timezone: string
  bio: string | null
  avatarColor: string
}

const TIMEZONES = ['UTC', 'America/New_York', 'America/Los_Angeles', 'Europe/London', 'Europe/Berlin', 'Asia/Kolkata', 'Asia/Tokyo', 'Australia/Sydney']

async function requestProfile(): Promise<Profile> {
  const response = await fetch('/api/account/profile', { cache: 'no-store' })
  const body = await response.json().catch(() => ({}))
  if (!response.ok || !body.profile) throw new Error(body.error ?? 'Profile data is unavailable.')
  return body.profile as Profile
}

export default function ProfileSettingsPage() {
  const toast = useToast()
  const [profile, setProfile] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [busy, setBusy] = useState(false)

  async function loadProfile() {
    setLoading(true)
    setLoadError('')
    try {
      setProfile(await requestProfile())
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Profile data is unavailable.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    void requestProfile()
      .then((nextProfile) => {
        if (!cancelled) setProfile(nextProfile)
      })
      .catch((error: unknown) => {
        if (!cancelled) setLoadError(error instanceof Error ? error.message : 'Profile data is unavailable.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  async function save() {
    if (!profile) return
    setBusy(true)
    try {
      const res = await fetch('/api/account/profile', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: profile.name,
          title: profile.title,
          phone: profile.phone,
          timezone: profile.timezone,
          bio: profile.bio,
          avatarColor: profile.avatarColor,
        }),
      })
      if (!res.ok) throw new Error()
      // Reflect changes in the topbar/session immediately.
      useConfigStore.setState((s) => ({
        user: s.user ? { ...s.user, name: profile.name, avatarColor: profile.avatarColor, title: profile.title } : s.user,
      }))
      toast.success('Profile updated')
    } catch {
      toast.error('Could not update profile')
    } finally {
      setBusy(false)
    }
  }

  if (loadError && !profile) {
    return (
      <SettingsCard title="Profile" description="Update your personal information.">
        <ErrorState description={loadError} onRetry={loadProfile} />
      </SettingsCard>
    )
  }

  if (loading || !profile) {
    return (
      <SettingsCard title="Profile" description="Update your personal information.">
        <div className="space-y-4">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      </SettingsCard>
    )
  }

  return (
    <SettingsCard
      title="Profile"
      description="This information may be visible to other members of your team."
      footer={
        <Button onClick={save} loading={busy}>
          Save changes
        </Button>
      }
    >
      <div className="space-y-5">
        <div className="flex items-center gap-4">
          <Avatar name={profile.name} color={profile.avatarColor} size="lg" />
          <div>
            <div className="flex items-center gap-2">
              <p className="font-medium text-foreground">{profile.name}</p>
              <Badge tone="accent">{ROLE_LABELS[profile.role as Role] ?? profile.role}</Badge>
            </div>
            <p className="text-sm text-muted">{profile.email}</p>
          </div>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-foreground">Avatar color</p>
          <div className="flex flex-wrap gap-2">
            {ACCENT_COLORS.map((c) => (
              <button
                key={c.key}
                onClick={() => setProfile({ ...profile, avatarColor: c.value })}
                aria-label={c.label}
                className={cn(
                  'size-8 rounded-full ring-2 ring-transparent transition-transform hover:scale-110',
                  profile.avatarColor === c.value && 'ring-offset-2 ring-offset-card',
                )}
                style={{ backgroundColor: c.value, ...(profile.avatarColor === c.value ? { ['--tw-ring-color' as string]: c.value } : {}) }}
              />
            ))}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Full name">
            <Input value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} />
          </Field>
          <Field label="Email" hint="Contact an admin to change your email.">
            <Input value={profile.email} disabled />
          </Field>
          <Field label="Job title">
            <Input value={profile.title ?? ''} onChange={(e) => setProfile({ ...profile, title: e.target.value })} />
          </Field>
          <Field label="Phone">
            <Input value={profile.phone ?? ''} onChange={(e) => setProfile({ ...profile, phone: e.target.value })} />
          </Field>
          <Field label="Timezone">
            <Select
              options={TIMEZONES.map((t) => ({ label: t, value: t }))}
              value={profile.timezone}
              onChange={(e) => setProfile({ ...profile, timezone: e.target.value })}
            />
          </Field>
        </div>

        <Field label="Bio">
          <Textarea
            value={profile.bio ?? ''}
            onChange={(e) => setProfile({ ...profile, bio: e.target.value })}
            placeholder="Tell your team a little about yourself…"
          />
        </Field>
      </div>
    </SettingsCard>
  )
}
