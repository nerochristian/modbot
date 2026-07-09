'use client'

import { useState } from 'react'
import { Megaphone } from 'lucide-react'
import { SettingsCard } from '@/components/dashboard/setting-section'
import { Field, Input, Textarea } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { useToast } from '@/components/ui/toast'
import { ROLES, ROLE_LABELS } from '@/lib/rbac'

export default function BroadcastAdminPage() {
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [form, setForm] = useState({ title: '', body: '', level: 'info', audience: 'all' })

  async function send() {
    setBusy(true)
    setErrors({})
    try {
      const res = await fetch('/api/admin/broadcast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        if (data.issues) {
          const fe: Record<string, string> = {}
          for (const i of data.issues) fe[i.path[0]] = i.message
          setErrors(fe)
        } else setErrors({ form: data.error ?? 'Could not send broadcast' })
        return
      }
      toast.success('Broadcast sent', `Delivered to ${data.recipients} user${data.recipients === 1 ? '' : 's'}.`)
      setForm({ title: '', body: '', level: 'info', audience: 'all' })
    } catch {
      setErrors({ form: 'Network error' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <SettingsCard
      title="Broadcast notification"
      description="Send an in-app notification to a group of users."
      footer={
        <Button onClick={send} loading={busy} disabled={!form.title || !form.body}>
          <Megaphone className="size-4" />
          Send broadcast
        </Button>
      }
    >
      <div className="space-y-4">
        {errors.form && (
          <div className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">{errors.form}</div>
        )}
        <Field label="Title" error={errors.title}>
          <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="e.g. Scheduled maintenance" />
        </Field>
        <Field label="Message" error={errors.body}>
          <Textarea value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} placeholder="What do you want to tell your users?" />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Level">
            <Select
              options={[
                { label: 'Info', value: 'info' },
                { label: 'Success', value: 'success' },
                { label: 'Warning', value: 'warning' },
                { label: 'Error', value: 'error' },
              ]}
              value={form.level}
              onChange={(e) => setForm({ ...form, level: e.target.value })}
            />
          </Field>
          <Field label="Audience">
            <Select
              options={[{ label: 'All users', value: 'all' }, ...ROLES.map((r) => ({ label: `${ROLE_LABELS[r]}s only`, value: r }))]}
              value={form.audience}
              onChange={(e) => setForm({ ...form, audience: e.target.value })}
            />
          </Field>
        </div>
      </div>
    </SettingsCard>
  )
}
