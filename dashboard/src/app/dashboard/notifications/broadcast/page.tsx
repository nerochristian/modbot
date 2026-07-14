'use client'

import { useState } from 'react'
import { Megaphone } from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { SettingsCard } from '@/components/dashboard/setting-section'
import { Button } from '@/components/ui/button'
import { Field, Input, Textarea } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { useToast } from '@/components/ui/toast'

export default function BroadcastPage() {
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [form, setForm] = useState({ title: '', body: '', level: 'info', audience: 'all' })

  async function send() {
    setBusy(true)
    setErrors({})
    try {
      const response = await fetch('/api/admin/broadcast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        if (data.issues) {
          const fieldErrors: Record<string, string> = {}
          for (const issue of data.issues) fieldErrors[issue.path[0]] = issue.message
          setErrors(fieldErrors)
        } else {
          setErrors({ form: data.error ?? 'Could not send broadcast' })
        }
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
    <>
      <PageHeader
        eyebrow="Inbox"
        title="Broadcast"
        description="Send an in-app notification to this server's dashboard administrators."
      />
      <SettingsCard
        title="Compose notification"
        description="The message appears in each recipient's Docket inbox."
        footer={
          <Button onClick={send} loading={busy} disabled={!form.title || !form.body}>
            <Megaphone className="size-4" />
            Send broadcast
          </Button>
        }
      >
        <div className="space-y-4">
          {errors.form && <div className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">{errors.form}</div>}
          <Field label="Title" error={errors.title}>
            <Input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="e.g. Scheduled maintenance" />
          </Field>
          <Field label="Message" error={errors.body}>
            <Textarea value={form.body} onChange={(event) => setForm({ ...form, body: event.target.value })} placeholder="What should dashboard administrators know?" />
          </Field>
          <Field label="Level">
            <Select
              options={[
                { label: 'Info', value: 'info' },
                { label: 'Success', value: 'success' },
                { label: 'Warning', value: 'warning' },
                { label: 'Error', value: 'error' },
              ]}
              value={form.level}
              onChange={(event) => setForm({ ...form, level: event.target.value })}
            />
          </Field>
        </div>
      </SettingsCard>
    </>
  )
}
