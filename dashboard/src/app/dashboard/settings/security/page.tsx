'use client'

import { useEffect, useState } from 'react'
import { Monitor, LogOut } from 'lucide-react'
import { SettingsCard, SettingRow } from '@/components/dashboard/setting-section'
import { Field, Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/components/ui/toast'
import { useConfigStore } from '@/lib/store'
import { formatDistanceToNow } from 'date-fns'

type Session = { id: string; userAgent: string | null; ip: string | null; createdAt: string; current: boolean }

export default function SecuritySettingsPage() {
  const toast = useToast()
  const [pwd, setPwd] = useState({ currentPassword: '', newPassword: '', confirm: '' })
  const [pwdBusy, setPwdBusy] = useState(false)
  const [pwdError, setPwdError] = useState('')
  const [twoFactor, setTwoFactor] = useState(false)
  const [sessions, setSessions] = useState<Session[]>([])

  useEffect(() => {
    fetch('/api/auth/session').then((r) => r.json()).then((d) => setTwoFactor(!!d.user?.twoFactorEnabled))
    loadSessions()
  }, [])

  function loadSessions() {
    fetch('/api/account/sessions').then((r) => r.json()).then((d) => setSessions(d.sessions ?? []))
  }

  async function changePassword() {
    setPwdError('')
    if (pwd.newPassword !== pwd.confirm) {
      setPwdError('New passwords do not match.')
      return
    }
    setPwdBusy(true)
    try {
      const res = await fetch('/api/account/password', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ currentPassword: pwd.currentPassword, newPassword: pwd.newPassword }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) {
        setPwdError(body.error ?? (body.issues?.[0]?.message ?? 'Could not change password'))
        return
      }
      toast.success('Password changed. Other sessions signed out.')
      setPwd({ currentPassword: '', newPassword: '', confirm: '' })
      loadSessions()
    } catch {
      setPwdError('Network error')
    } finally {
      setPwdBusy(false)
    }
  }

  async function toggle2fa(enabled: boolean) {
    setTwoFactor(enabled)
    await fetch('/api/account/2fa', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled }),
    }).catch(() => undefined)
    useConfigStore.setState((s) => ({ user: s.user }))
    toast.success(enabled ? 'Two-factor authentication enabled' : 'Two-factor authentication disabled')
  }

  async function signOutOthers() {
    await fetch('/api/account/sessions', { method: 'DELETE' }).catch(() => undefined)
    toast.success('Signed out of other devices')
    loadSessions()
  }

  return (
    <>
      <SettingsCard
        title="Password"
        description="Change your password. This will sign you out of all other devices."
        footer={
          <Button onClick={changePassword} loading={pwdBusy}>
            Update password
          </Button>
        }
      >
        <div className="space-y-4">
          {pwdError && (
            <div className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">{pwdError}</div>
          )}
          <Field label="Current password">
            <Input type="password" value={pwd.currentPassword} onChange={(e) => setPwd({ ...pwd, currentPassword: e.target.value })} />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="New password" hint="At least 8 characters.">
              <Input type="password" value={pwd.newPassword} onChange={(e) => setPwd({ ...pwd, newPassword: e.target.value })} />
            </Field>
            <Field label="Confirm new password">
              <Input type="password" value={pwd.confirm} onChange={(e) => setPwd({ ...pwd, confirm: e.target.value })} />
            </Field>
          </div>
        </div>
      </SettingsCard>

      <SettingsCard title="Two-factor authentication" description="Add an extra layer of security to your account.">
        <SettingRow
          label="Authenticator app"
          description="Require a one-time code from an authenticator app when signing in."
        >
          <div className="flex items-center gap-3">
            <Badge tone={twoFactor ? 'success' : 'neutral'}>{twoFactor ? 'Enabled' : 'Disabled'}</Badge>
            <Switch checked={twoFactor} onChange={toggle2fa} label="Toggle two-factor authentication" />
          </div>
        </SettingRow>
      </SettingsCard>

      <SettingsCard
        title="Active sessions"
        description="Devices currently signed in to your account."
        footer={
          sessions.length > 1 ? (
            <Button variant="outline" onClick={signOutOthers}>
              <LogOut className="size-4" />
              Sign out other devices
            </Button>
          ) : undefined
        }
      >
        <ul className="divide-y divide-border">
          {sessions.map((s) => (
            <li key={s.id} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
              <span className="flex size-9 items-center justify-center rounded-lg bg-surface-2 text-muted">
                <Monitor className="size-4.5" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">
                  {s.userAgent?.split(')')[0]?.replace('Mozilla/5.0 (', '') ?? 'Unknown device'}
                </p>
                <p className="text-xs text-muted">
                  {s.ip ?? 'unknown IP'} · started {formatDistanceToNow(new Date(s.createdAt), { addSuffix: true })}
                </p>
              </div>
              {s.current && <Badge tone="success" dot>This device</Badge>}
            </li>
          ))}
        </ul>
      </SettingsCard>
    </>
  )
}
