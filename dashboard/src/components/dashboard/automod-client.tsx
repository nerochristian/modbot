'use client'

import { useState } from 'react'
import { LayoutTemplate, Pencil, ShieldOff, ShieldAlert, X } from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { GuidedTour, type TourStep } from '@/components/dashboard/tour-engine'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge, severityTone, severityRail, TickMeter } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Select } from '@/components/ui/select'
import { Field, Input, Textarea } from '@/components/ui/input'
import { Modal, ConfirmDialog } from '@/components/ui/modal'
import { EmptyState, ErrorState } from '@/components/ui/empty-state'
import { Spinner } from '@/components/ui/spinner'
import { useToast } from '@/components/ui/toast'
import { AUTOMOD_DEFINITIONS } from '@/lib/automod-contract'
import { AUTOMOD_TEMPLATES, type AutomodTemplate } from '@/lib/automod-templates'
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
  durationSeconds: number | null
  deleteMessage: boolean
  severity: string
  exemptRoles: string[]
  enabled: boolean
  hits: number
  lastTriggeredAt: string | null
  createdAt: string
  updatedAt: string
}
type Payload = { data: Rule[]; totalHits: number; activeCount: number }

const AUTOMOD_TOUR_STEPS: readonly TourStep[] = [
  {
    eyebrow: 'AutoMod, explained',
    title: 'Fifteen detectors, all yours',
    description: 'Every detector is off until you turn it on. Pick a template for instant cover, or build your own setup rule by rule.',
  },
  {
    target: 'automod-templates',
    eyebrow: 'Templates',
    title: 'One-click rule sets',
    description: 'Open a template to see exactly which rules it turns on, which words it blocks, and which links it stops. Edit any of it before applying — and after.',
  },
  {
    target: 'automod-rules',
    eyebrow: 'Rules',
    title: 'Tune each detector',
    description: 'Flip a rule on, choose its punishment, and decide whether flagged messages get deleted. Deletion is the switch inside Edit — the action only picks the punishment.',
  },
  {
    eyebrow: 'After the block',
    title: 'Hits show up in Activity',
    description: 'Every blocked message lands in Activity and your AutoMod log channel. Changes apply within about fifteen seconds — no restarts.',
    action: { label: 'Open Activity', href: '/dashboard/activity' },
  },
]
type GuildRole = { id: string; name: string; position: number; color: number }
type GuildResourcesPayload = { roles: GuildRole[] }

const TRIGGER_LABELS: Record<string, string> = {
  badwords: 'Blocked words',
  spam: 'Spam',
  mentions: 'Mention spam',
  invites: 'Invite links',
  links: 'Links',
  caps: 'Excessive caps',
  duplicates: 'Duplicate messages',
  fast_messages: 'Fast messages',
  emoji_spam: 'Emoji spam',
  wall_spam: 'Wall / spacer spam',
  attachments: 'Attachments',
  unicode_spam: 'Zalgo & symbol spam',
  new_accounts: 'New accounts',
  raid: 'Raid protection',
}

const ACTION_LABELS: Record<string, string> = {
  none: 'No action',
  log: 'Log only',
  warn: 'Warn',
  timeout: 'Timeout',
  kick: 'Kick',
  ban: 'Ban',
}

const ACTION_OPTIONS = Object.entries(ACTION_LABELS).map(([value, label]) => ({ value, label }))

type Tone = 'neutral' | 'accent' | 'mint' | 'success' | 'warning' | 'danger' | 'info'
const ACTION_TONE: Record<string, Tone> = {
  none: 'neutral',
  log: 'neutral',
  warn: 'info',
  timeout: 'warning',
  kick: 'warning',
  ban: 'danger',
}

// Pattern field config per trigger. `null` hides the pattern input entirely.
const PATTERN_CONFIG: Record<string, { label: string; placeholder: string } | null> = {
  badwords: { label: 'Comma-separated keywords', placeholder: 'scam, free nitro, @everyone' },
  spam: { label: 'Max messages / 10s', placeholder: '5' },
  mentions: { label: 'Max mentions per message', placeholder: '5' },
  caps: { label: 'Max % caps', placeholder: '70' },
  duplicates: { label: 'Duplicate threshold', placeholder: '3' },
  fast_messages: { label: 'Fast-message threshold', placeholder: '5' },
  emoji_spam: { label: 'Emoji threshold', placeholder: '12' },
  wall_spam: { label: 'Maximum lines', placeholder: '12' },
  unicode_spam: { label: 'Maximum symbol ratio', placeholder: '70' },
  new_accounts: { label: 'Account age in days', placeholder: '7' },
  raid: { label: 'Join threshold', placeholder: '10' },
  invites: null,
  links: { label: 'Blocked domains', placeholder: 'grabify.link, iplogger.org, bit.ly' },
  attachments: { label: 'Attachment threshold', placeholder: '5' },
}

export function AutomodClient() {
  const toast = useToast()
  const canWrite = useConfigStore((s) => s.can('automod.write'))
  const { data, loading, error, refetch } = useApi<Payload>('/api/automod')

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
      toast.success('Rule disabled')
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
        eyebrow="Rulebook"
        title="Automod"
        description={
          data
            ? `${data.data.length} rules · ${data.activeCount} active · ${formatNumber(data.totalHits)} total hits`
            : 'Filter messages automatically before your team has to.'
        }
      />

      <TemplateGallery canWrite={canWrite} onApplied={refetch} />
      <GuidedTour steps={AUTOMOD_TOUR_STEPS} storageKey="docket:tour:automod:v1" />

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
            description="The bot runtime did not return any configurable modules."
          />
        </Card>
      ) : data ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" data-tour="automod-rules">
          {data.data.map((rule) => (
            <Card
              key={rule.id}
              className={cn(severityRail(rule.severity), 'relative overflow-hidden', !rule.enabled && 'opacity-60')}
            >
              <div className="space-y-3 p-4 pl-5">
                <div className="flex items-start justify-between gap-3">
                  <h3 className="min-w-0 truncate font-display font-semibold text-foreground">{rule.name}</h3>
                  <Switch
                    checked={rule.enabled}
                    disabled={!canWrite || toggling === rule.id}
                    onChange={() => handleToggle(rule)}
                    label={`Toggle ${rule.name}`}
                  />
                </div>

                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge tone="neutral">{TRIGGER_LABELS[rule.trigger] ?? rule.trigger}</Badge>
                  <TickMeter severity={rule.severity} />
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
                    {rule.deleteMessage && (
                      <span className="text-muted-2" title="Flagged messages are deleted">
                        + deletes msgs
                      </span>
                    )}
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
                      aria-label={`Disable ${rule.name}`}
                    >
                      <ShieldOff className="size-4" />
                    </Button>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      ) : null}

      {editing && (
        <RuleBuilder
          rule={editing}
          onClose={() => {
            setEditing(null)
          }}
          onSaved={() => {
            setEditing(null)
            refetch()
          }}
        />
      )}

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={handleDelete}
        title="Disable rule"
        description={`Disable "${deleting?.name}"? You can enable it again at any time.`}
        confirmLabel="Disable"
        loading={delBusy}
      />
    </>
  )
}

function TemplateGallery({ canWrite, onApplied }: { canWrite: boolean; onApplied: () => void }) {
  const [active, setActive] = useState<AutomodTemplate | null>(null)

  return (
    <>
      <Card className="mb-4 p-4" data-tour="automod-templates">
        <div className="flex items-center gap-3">
          <span className="grid size-9 place-items-center rounded-lg border border-accent-line bg-accent-soft text-accent">
            <LayoutTemplate className="size-4" />
          </span>
          <div>
            <h2 className="font-display text-sm font-semibold text-foreground">Start from a template</h2>
            <p className="text-xs text-muted">Apply a full rule set in one click — every toggle, word list, and link list stays editable.</p>
          </div>
        </div>
        <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {AUTOMOD_TEMPLATES.map((template) => {
            const enabledCount = AUTOMOD_DEFINITIONS.filter((d) => template.settings[d.enabledKey] === true).length
            return (
              <button
                key={template.id}
                type="button"
                onClick={() => setActive(template)}
                className="group rounded-xl border border-border bg-surface-2/40 p-3 text-left transition hover:border-accent-line hover:bg-accent-soft/30"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="font-display text-sm font-semibold text-foreground">{template.name}</p>
                  <Badge tone="accent">{enabledCount}/15 on</Badge>
                </div>
                <p className="mt-0.5 text-xs text-muted">{template.tagline}</p>
              </button>
            )
          })}
        </div>
      </Card>
      {active && (
        <TemplateSheet
          template={active}
          canWrite={canWrite}
          onClose={() => setActive(null)}
          onApplied={() => {
            setActive(null)
            onApplied()
          }}
        />
      )}
    </>
  )
}

function TemplateSheet({
  template,
  canWrite,
  onClose,
  onApplied,
}: {
  template: AutomodTemplate
  canWrite: boolean
  onClose: () => void
  onApplied: () => void
}) {
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [draft, setDraft] = useState<Record<string, unknown>>(() => structuredClone(template.settings))

  const ruleActions = (draft.automod_rule_actions ?? {}) as Record<string, { action?: string; delete?: boolean }>

  function setKey(key: string, value: unknown) {
    setDraft((current) => ({ ...current, [key]: value }))
  }
  function setRuleAction(id: string, action: string) {
    setDraft((current) => ({
      ...current,
      automod_rule_actions: { ...((current.automod_rule_actions as object) ?? {}), [id]: { action, delete: true } },
    }))
  }
  const listValue = (key: string) => (Array.isArray(draft[key]) ? (draft[key] as string[]).join(', ') : '')
  const setList = (key: string, text: string) => setKey(key, text.split(',').map((item) => item.trim()).filter(Boolean))

  async function apply() {
    setBusy(true)
    setError(null)
    try {
      const res = await fetch('/api/automod/template', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: template.name, settings: draft }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) {
        setError(body.error ?? 'Could not apply template')
        return
      }
      toast.success(`${template.name} template applied`)
      onApplied()
    } catch {
      setError('Network error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`${template.name} template`}
      description={template.description}
      size="xl"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={apply} loading={busy} disabled={!canWrite}>
            Apply template
          </Button>
        </>
      }
    >
      <div className="space-y-5">
        {error && (
          <div className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">{error}</div>
        )}

        <div>
          <p className="mb-2 font-mono text-[0.625rem] font-bold uppercase tracking-[0.18em] text-accent">Rules on / off</p>
          <div className="grid gap-1.5 sm:grid-cols-2">
            {AUTOMOD_DEFINITIONS.map((definition) => {
              const on = draft[definition.enabledKey] === true
              return (
                <div
                  key={definition.id}
                  className={cn(
                    'flex items-center justify-between gap-2 rounded-lg border px-3 py-2 transition-colors',
                    on ? 'border-accent-line bg-accent-soft/30' : 'border-border bg-surface-2/40 opacity-70',
                  )}
                  title={definition.description}
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-foreground">{definition.name}</p>
                    {on && (
                      <Select
                        className="mt-1 h-7 w-32 text-xs"
                        options={ACTION_OPTIONS}
                        value={ruleActions[definition.id]?.action ?? 'warn'}
                        onChange={(event) => setRuleAction(definition.id, event.target.value)}
                      />
                    )}
                  </div>
                  <Switch
                    checked={on}
                    disabled={!canWrite}
                    onChange={(value) => setKey(definition.enabledKey, value)}
                    label={`Toggle ${definition.name}`}
                  />
                </div>
              )
            })}
          </div>
        </div>

        <div className="space-y-3">
          <p className="font-mono text-[0.625rem] font-bold uppercase tracking-[0.18em] text-accent">Lists & link policy</p>
          <Field label="Blocked words" hint="Comma-separated. Matched even through leetspeak and spacing tricks.">
            <Textarea
              className="font-mono text-xs"
              value={listValue('automod_badwords')}
              onChange={(event) => setList('automod_badwords', event.target.value)}
              placeholder="Leave empty for no word filter"
              rows={2}
            />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Blocked domains" hint="IP grabbers, sketchy shorteners, scam lookalikes.">
              <Textarea
                className="font-mono text-xs"
                value={listValue('automod_links_blocklist')}
                onChange={(event) => setList('automod_links_blocklist', event.target.value)}
                placeholder="grabify.link, iplogger.org, bit.ly"
                rows={3}
              />
            </Field>
            <Field label="Allowed domains (always pass)" hint="These always bypass the link filter.">
              <Textarea
                className="font-mono text-xs"
                value={listValue('automod_links_whitelist')}
                onChange={(event) => setList('automod_links_whitelist', event.target.value)}
                placeholder="discord.com, youtube.com, github.com"
                rows={3}
              />
            </Field>
          </div>
          <Field label="Link filter mode" hint="Dangerous blocks the list above; allowlist blocks every link except allowed domains.">
            <Select
              options={[
                { label: 'Block dangerous links only', value: 'dangerous' },
                { label: 'Allow only listed domains', value: 'allowlist' },
              ]}
              value={String(draft.automod_links_mode ?? 'dangerous')}
              onChange={(event) => setKey('automod_links_mode', event.target.value)}
            />
          </Field>
        </div>
      </div>
    </Modal>
  )
}

function RuleBuilder({
  rule,
  onClose,
  onSaved,
}: {
  rule: Rule
  onClose: () => void
  onSaved: () => void
}) {
  const toast = useToast()
  const { data: resources, loading: resourcesLoading, error: resourcesError, refetch: refetchResources } =
    useApi<GuildResourcesPayload>('/api/guilds/resources')
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [form, setForm] = useState({
    trigger: rule.trigger,
    pattern: rule.pattern ?? '',
    action: rule.action,
    durationSeconds: rule.durationSeconds ? String(rule.durationSeconds) : '',
    deleteMessage: rule.deleteMessage,
    exemptRoles: rule.exemptRoles,
    enabled: rule.enabled,
  })

  const patternConfig = PATTERN_CONFIG[form.trigger]

  async function submit() {
    setBusy(true)
    setErrors({})
    try {
      const payload = {
        trigger: form.trigger,
        pattern: form.pattern || null,
        action: form.action,
        durationSeconds: form.durationSeconds ? Number(form.durationSeconds) : null,
        deleteMessage: form.deleteMessage,
        exemptRoles: form.exemptRoles,
        enabled: form.enabled,
      }
      const res = await fetch(`/api/automod/${rule.id}`, {
        method: 'PATCH',
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
      toast.success('Rule updated')
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
      title={`Edit ${rule.name}`}
      size="lg"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={busy}>
            Save changes
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

        <div className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm text-muted">
          Runtime module: <span className="font-medium text-foreground">{TRIGGER_LABELS[form.trigger] ?? form.trigger}</span>
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

        <div className={form.action === 'timeout' ? 'grid grid-cols-2 gap-4' : undefined}>
          <Field label="Action" error={errors.action}>
            <Select
              options={ACTION_OPTIONS}
              value={form.action}
              onChange={(e) => setForm({ ...form, action: e.target.value })}
            />
          </Field>
          {form.action === 'timeout' ? (
            <Field label="Timeout duration" error={errors.durationSeconds} hint="Seconds, from 60 to 2,419,200">
              <Input
                inputMode="numeric"
                value={form.durationSeconds}
                onChange={(e) => setForm({ ...form, durationSeconds: e.target.value })}
                placeholder="3600"
              />
            </Field>
          ) : null}
        </div>

        <AutomodRolePicker
          roles={resources?.roles ?? []}
          selected={form.exemptRoles}
          loading={resourcesLoading}
          error={resourcesError || errors.exemptRoles}
          disabled={busy}
          onRetry={() => void refetchResources()}
          onChange={(exemptRoles) => setForm({ ...form, exemptRoles })}
        />

        <div className="flex items-center justify-between rounded-lg border border-border bg-surface-2/50 px-3 py-2.5">
          <div>
            <p className="text-sm font-medium text-foreground">Delete matched messages</p>
            <p className="text-xs text-muted">Remove the violating message when this module triggers.</p>
          </div>
          <Switch
            checked={form.deleteMessage}
            onChange={(value) => setForm({ ...form, deleteMessage: value })}
            label="Delete matched messages"
          />
        </div>

      </div>
    </Modal>
  )
}

function AutomodRolePicker({
  roles,
  selected,
  loading,
  error,
  disabled,
  onRetry,
  onChange,
}: {
  roles: GuildRole[]
  selected: string[]
  loading: boolean
  error?: string
  disabled: boolean
  onRetry: () => void
  onChange: (roles: string[]) => void
}) {
  const [nextRole, setNextRole] = useState('')
  const available = roles.filter((role) => !selected.includes(role.id))

  return (
    <Field
      label="AutoMod bypass roles"
      htmlFor="automod-bypass-role"
      hint="Global setting: members in these roles bypass every AutoMod rule, not only the rule currently open."
      error={error}
    >
      <div className="flex gap-2">
        <Select
          id="automod-bypass-role"
          value={nextRole}
          disabled={disabled || loading || available.length === 0}
          options={available.map((role) => ({ label: `@${role.name}`, value: role.id }))}
          placeholder={loading ? 'Loading roles…' : available.length > 0 ? 'Select role' : 'No more roles'}
          onChange={(event) => {
            const roleId = event.target.value
            setNextRole('')
            if (roleId && !selected.includes(roleId)) onChange([...selected, roleId])
          }}
        />
        {error && (
          <Button type="button" variant="ghost" size="sm" onClick={onRetry}>
            Retry
          </Button>
        )}
      </div>
      {selected.length > 0 && (
        <ul className="flex flex-wrap gap-1.5">
          {selected.map((roleId) => {
            const role = roles.find((candidate) => candidate.id === roleId)
            return (
              <li key={roleId} className="inline-flex max-w-full items-center gap-1.5 rounded-md border border-border bg-surface px-2 py-1 text-xs text-foreground">
                <span className="truncate">{role ? `@${role.name}` : `Unknown role · ${roleId}`}</span>
                <button
                  type="button"
                  className="focus-ring rounded-sm text-muted-2 hover:text-danger"
                  disabled={disabled}
                  aria-label={`Remove ${role?.name ?? roleId}`}
                  onClick={() => onChange(selected.filter((candidate) => candidate !== roleId))}
                >
                  <X className="size-3.5" />
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </Field>
  )
}
