'use client'

import { useState } from 'react'
import { Plus, Pencil, Trash2, ShieldAlert } from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge, severityTone, severitySpine } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Select } from '@/components/ui/select'
import { Field, Input } from '@/components/ui/input'
import { Modal, ConfirmDialog } from '@/components/ui/modal'
import { EmptyState, ErrorState } from '@/components/ui/empty-state'
import { Spinner } from '@/components/ui/spinner'
import { useToast } from '@/components/ui/toast'
import { useConfigStore } from '@/lib/store'
import { useApi } from '@/lib/use-api'
import { formatNumber, cn } from '@/lib/utils'

type Rule = {
  id: string
  name: string
  description: string | null
  trigger: string
  pattern: string | null
  action: string
  severity: string
  exemptRoles: string[]
  enabled: boolean
  hits: number
  lastTriggeredAt: string | null
  createdAt: string
  updatedAt: string
}
type Payload = { data: Rule[]; totalHits: number; activeCount: number }

const TRIGGER_LABELS: Record<string, string> = {
  keyword: 'Keyword filter',
  regex: 'Regex match',
  spam: 'Spam',
  mention_spam: 'Mention spam',
  invite: 'Invite links',
  link: 'Links',
  caps: 'Excessive caps',
  attachment: 'Attachments',
}

const TRIGGER_OPTIONS = Object.entries(TRIGGER_LABELS).map(([value, label]) => ({ value, label }))

const ACTION_LABELS: Record<string, string> = {
  delete: 'Delete',
  warn: 'Warn',
  mute: 'Mute',
  timeout: 'Timeout',
  kick: 'Kick',
  ban: 'Ban',
  flag: 'Flag',
}

const ACTION_OPTIONS = Object.entries(ACTION_LABELS).map(([value, label]) => ({ value, label }))

const SEVERITY_OPTIONS = [
  { label: 'Low', value: 'low' },
  { label: 'Medium', value: 'medium' },
  { label: 'High', value: 'high' },
  { label: 'Critical', value: 'critical' },
]

type Tone = 'neutral' | 'accent' | 'mint' | 'success' | 'warning' | 'danger' | 'info'
const ACTION_TONE: Record<string, Tone> = {
  delete: 'neutral',
  warn: 'info',
  mute: 'warning',
  timeout: 'warning',
  kick: 'warning',
  ban: 'danger',
  flag: 'accent',
}

// Pattern field config per trigger. `null` hides the pattern input entirely.
const PATTERN_CONFIG: Record<string, { label: string; placeholder: string } | null> = {
  keyword: { label: 'Comma-separated keywords', placeholder: 'scam, free nitro, @everyone' },
  regex: { label: 'Regular expression', placeholder: '(?i)free\\s*nitro' },
  spam: { label: 'Max messages / 10s', placeholder: '5' },
  mention_spam: { label: 'Max mentions per message', placeholder: '5' },
  caps: { label: 'Max % caps', placeholder: '70' },
  invite: null,
  link: null,
  attachment: null,
}

export function AutomodClient() {
  const toast = useToast()
  const canWrite = useConfigStore((s) => s.can('automod.write'))
  const { data, loading, error, refetch } = useApi<Payload>('/api/automod')

  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<Rule | null>(null)
  const [deleting, setDeleting] = useState<Rule | null>(null)
  const [delBusy, setDelBusy] = useState(false)
  const [toggling, setToggling] = useState<string | null>(null)

  async function handleToggle(rule: Rule) {
    setToggling(rule.id)
    try {
      const res = await fetch(`/api/automod/${rule.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !rule.enabled }),
      })
      if (!res.ok) throw new Error()
      toast.success(rule.enabled ? 'Rule disabled' : 'Rule enabled')
      refetch()
    } catch {
      toast.error('Failed to update rule')
    } finally {
      setToggling(null)
    }
  }

  async function handleDelete() {
    if (!deleting) return
    setDelBusy(true)
    try {
      const res = await fetch(`/api/automod/${deleting.id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error()
      toast.success('Rule deleted')
      setDeleting(null)
      refetch()
    } catch {
      toast.error('Failed to delete rule')
    } finally {
      setDelBusy(false)
    }
  }

  return (
    <>
      <PageHeader
        title="Automod"
        description={
          data
            ? `${data.data.length} rules · ${data.activeCount} active · ${formatNumber(data.totalHits)} total hits`
            : 'Filter messages automatically before your team has to.'
        }
        actions={
          canWrite && data && data.data.length > 0 ? (
            <Button size="sm" onClick={() => setCreating(true)}>
              <Plus className="size-4" />
              New rule
            </Button>
          ) : undefined
        }
      />

      {error && !data ? (
        <Card>
          <ErrorState onRetry={refetch} description={error} />
        </Card>
      ) : loading && !data ? (
        <div className="flex items-center justify-center py-24">
          <Spinner className="size-6" />
        </div>
      ) : data && data.data.length === 0 ? (
        <Card>
          <EmptyState
            icon={ShieldAlert}
            title="No automod rules"
            description="Create your first rule to start filtering automatically."
            action={
              canWrite ? (
                <Button size="sm" onClick={() => setCreating(true)}>
                  <Plus className="size-4" />
                  New rule
                </Button>
              ) : undefined
            }
          />
        </Card>
      ) : data ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {data.data.map((rule) => (
            <Card
              key={rule.id}
              className={cn(severitySpine(rule.severity), 'relative overflow-hidden', !rule.enabled && 'opacity-60')}
            >
              <div className="space-y-3 p-4 pl-5">
                <div className="flex items-start justify-between gap-3">
                  <h3 className="min-w-0 truncate font-semibold text-foreground">{rule.name}</h3>
                  <Switch
                    checked={rule.enabled}
                    disabled={!canWrite || toggling === rule.id}
                    onChange={() => handleToggle(rule)}
                    label={`Toggle ${rule.name}`}
                  />
                </div>

                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge tone="neutral">{TRIGGER_LABELS[rule.trigger] ?? rule.trigger}</Badge>
                  <Badge tone={severityTone(rule.severity)}>{rule.severity}</Badge>
                </div>

                {rule.description && <p className="text-sm text-muted">{rule.description}</p>}

                {rule.pattern && (
                  <code className="mono-id block truncate rounded-md bg-surface-2 px-2 py-1 text-xs text-muted">
                    {rule.pattern}
                  </code>
                )}

                {rule.exemptRoles.length > 0 && (
                  <p className="truncate text-xs text-muted">Exempt: {rule.exemptRoles.join(', ')}</p>
                )}

                <div className="flex items-center justify-between gap-3 border-t border-border pt-3">
                  <div className="flex items-center gap-1.5 text-xs text-muted">
                    <span>Action:</span>
                    <Badge tone={ACTION_TONE[rule.action] ?? 'neutral'}>
                      {ACTION_LABELS[rule.action] ?? rule.action}
                    </Badge>
                  </div>
                  <span className="tabular-nums text-xs text-muted">{formatNumber(rule.hits)} hits</span>
                </div>

                {canWrite && (
                  <div className="flex items-center gap-2 pt-1">
                    <Button variant="ghost" size="sm" onClick={() => setEditing(rule)}>
                      <Pencil className="size-4" />
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="ml-auto text-muted hover:text-danger"
                      onClick={() => setDeleting(rule)}
                      aria-label={`Delete ${rule.name}`}
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      ) : null}

      {(creating || editing) && (
        <RuleBuilder
          rule={editing}
          onClose={() => {
            setCreating(false)
            setEditing(null)
          }}
          onSaved={() => {
            setCreating(false)
            setEditing(null)
            refetch()
          }}
        />
      )}

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={handleDelete}
        title="Delete rule"
        description={`Delete "${deleting?.name}"? Messages matching this rule will no longer be filtered. This cannot be undone.`}
        confirmLabel="Delete"
        destructive
        loading={delBusy}
      />
    </>
  )
}

function RuleBuilder({
  rule,
  onClose,
  onSaved,
}: {
  rule: Rule | null
  onClose: () => void
  onSaved: () => void
}) {
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [form, setForm] = useState({
    name: rule?.name ?? '',
    description: rule?.description ?? '',
    trigger: rule?.trigger ?? 'keyword',
    pattern: rule?.pattern ?? '',
    action: rule?.action ?? 'delete',
    severity: rule?.severity ?? 'medium',
    exemptRoles: rule?.exemptRoles.join(', ') ?? '',
    enabled: rule?.enabled ?? true,
  })

  const patternConfig = PATTERN_CONFIG[form.trigger]

  async function submit() {
    setBusy(true)
    setErrors({})
    try {
      const exemptRoles = form.exemptRoles
        .split(',')
        .map((r) => r.trim())
        .filter(Boolean)
      const payload = {
        name: form.name,
        description: form.description || null,
        trigger: form.trigger,
        pattern: form.pattern || null,
        action: form.action,
        severity: form.severity,
        exemptRoles,
        enabled: form.enabled,
      }
      const res = await fetch(rule ? `/api/automod/${rule.id}` : '/api/automod', {
        method: rule ? 'PATCH' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) {
        if (body.issues) {
          const fe: Record<string, string> = {}
          for (const i of body.issues) fe[i.path[0]] = i.message
          setErrors(fe)
        } else {
          setErrors({ form: body.error ?? 'Could not save rule' })
        }
        return
      }
      toast.success(rule ? 'Rule updated' : 'Rule created')
      onSaved()
    } catch {
      setErrors({ form: 'Network error' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={rule ? 'Edit rule' : 'New rule'}
      size="lg"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={busy}>
            {rule ? 'Save changes' : 'Create rule'}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {errors.form && (
          <div className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">
            {errors.form}
          </div>
        )}

        <Field label="Name" error={errors.name}>
          <Input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Block scam links"
          />
        </Field>

        <Field label="Description" error={errors.description}>
          <Input
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="Optional context for your team"
          />
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Trigger" error={errors.trigger}>
            <Select
              options={TRIGGER_OPTIONS}
              value={form.trigger}
              onChange={(e) => setForm({ ...form, trigger: e.target.value })}
            />
          </Field>
          <Field label="Severity" error={errors.severity}>
            <Select
              options={SEVERITY_OPTIONS}
              value={form.severity}
              onChange={(e) => setForm({ ...form, severity: e.target.value })}
            />
          </Field>
        </div>

        {patternConfig ? (
          <Field label={patternConfig.label} error={errors.pattern}>
            <Input
              className="font-mono"
              value={form.pattern}
              onChange={(e) => setForm({ ...form, pattern: e.target.value })}
              placeholder={patternConfig.placeholder}
            />
          </Field>
        ) : (
          <p className="text-xs text-muted">
            No pattern needed — this trigger matches {TRIGGER_LABELS[form.trigger].toLowerCase()} automatically.
          </p>
        )}

        <div className="grid grid-cols-2 gap-4">
          <Field label="Action" error={errors.action}>
            <Select
              options={ACTION_OPTIONS}
              value={form.action}
              onChange={(e) => setForm({ ...form, action: e.target.value })}
            />
          </Field>
          <Field label="Exempt roles" error={errors.exemptRoles} hint="Comma-separated role names">
            <Input
              value={form.exemptRoles}
              onChange={(e) => setForm({ ...form, exemptRoles: e.target.value })}
              placeholder="Moderator, Admin"
            />
          </Field>
        </div>

        <div className="flex items-center justify-between rounded-lg border border-border bg-surface-2/50 px-3 py-2.5">
          <div>
            <p className="text-sm font-medium text-foreground">Enabled</p>
            <p className="text-xs text-muted">Start filtering as soon as this rule is saved.</p>
          </div>
          <Switch
            checked={form.enabled}
            onChange={(v) => setForm({ ...form, enabled: v })}
            label="Enable rule"
          />
        </div>
      </div>
    </Modal>
  )
}
