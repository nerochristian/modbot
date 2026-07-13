'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import {
  ArrowUpRight,
  Blocks,
  Bot,
  CheckCircle2,
  CircleOff,
  ImageIcon,
  KeyRound,
  Loader2,
  Search,
  ScrollText,
  Settings2,
  ShieldCheck,
  ShieldAlert,
  Plus,
  Ticket,
  Trash2,
  UserCheck,
  UserPlus,
  X,
  type LucideIcon,
} from 'lucide-react'
import { PageHeader } from '@/components/dashboard/page-header'
import { Card } from '@/components/ui/card'
import { Button, buttonVariants } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Select } from '@/components/ui/select'
import { Field, Input } from '@/components/ui/input'
import { ConfirmDialog } from '@/components/ui/modal'
import { EmptyState, ErrorState } from '@/components/ui/empty-state'
import { useToast } from '@/components/ui/toast'
import { useConfigStore } from '@/lib/store'
import { useApi } from '@/lib/use-api'
import { cn } from '@/lib/utils'
import {
  isDiscordSnowflake,
  type AutopunishAction,
  type AutopunishRule,
  type ModuleField,
  type ModuleSpecial,
} from '@/lib/modules-contract'

type ModuleValues = Record<string, string | number | boolean | string[] | AutopunishRule[] | null>
type Module = {
  id: string
  name: string
  description: string
  category: string
  badge?: 'new' | 'standard' | 'premium' | 'core'
  enableKey: string | null
  settingsHref?: string
  special?: ModuleSpecial
  toggleable: boolean
  enabled: boolean
  fields: ModuleField[]
  values: ModuleValues
}
type Payload = { data: Module[]; enabledCount: number }

const BADGE_TONE = {
  new: 'success',
  standard: 'info',
  premium: 'warning',
  core: 'neutral',
} as const

const BADGE_LABEL = {
  new: 'New',
  standard: 'Standard',
  premium: 'Premium',
  core: 'Core',
} as const

type StatusFilter = 'all' | 'enabled' | 'disabled'

const CATEGORY_ORDER = ['Moderation', 'Access', 'Engagement'] as const

const CATEGORY_META: Record<string, { description: string; registerId: string }> = {
  Moderation: {
    description: 'Detection, enforcement, and staff authority.',
    registerId: 'REG / MOD',
  },
  Access: {
    description: 'Join gates, identity checks, and member roles.',
    registerId: 'REG / ACS',
  },
  Engagement: {
    description: 'Member-facing workflows and server records.',
    registerId: 'REG / ENG',
  },
}

const MODULE_ICONS: Record<string, LucideIcon> = {
  moderation: ShieldCheck,
  automod: ShieldAlert,
  aimod: Bot,
  antiraid: Blocks,
  verification: UserCheck,
  whitelist: KeyRound,
  tickets: Ticket,
  logging: ScrollText,
  welcome: ImageIcon,
  autoroles: UserPlus,
}

export function ModulesClient() {
  const { data, loading, error, refetch } = useApi<Payload>('/api/modules')
  const canWrite = useConfigStore((s) => s.can('config.write'))
  const toast = useToast()
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [toggling, setToggling] = useState<string | null>(null)
  const [editing, setEditing] = useState<Module | null>(null)
  const [pendingWhitelist, setPendingWhitelist] = useState<Module | null>(null)

  const modules = useMemo(() => data?.data ?? [], [data])
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return modules.filter(
      (m) =>
        (statusFilter === 'all' || (statusFilter === 'enabled' ? m.enabled : !m.enabled)) &&
        (!q ||
          m.id.toLowerCase().includes(q) ||
          m.name.toLowerCase().includes(q) ||
          m.description.toLowerCase().includes(q) ||
          m.category.toLowerCase().includes(q)),
    )
  }, [modules, query, statusFilter])

  const grouped = useMemo(
    () =>
      CATEGORY_ORDER.map((category) => ({
        category,
        modules: filtered.filter((mod) => mod.category === category),
        allModules: modules.filter((mod) => mod.category === category),
      })).filter((group) => group.modules.length > 0),
    [filtered, modules],
  )

  async function toggle(mod: Module, next: boolean) {
    if (!canWrite || !mod.toggleable) return
    setToggling(mod.id)
    try {
      const res = await fetch(`/api/modules/${mod.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: next }),
      })
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || 'Failed to update module')
      toast.success(`${mod.name} ${next ? 'enabled' : 'disabled'}`)
      await refetch()
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Try again in a moment.'
      toast.error(`${mod.name} was not changed`, message)
      if (next && /before enabling/i.test(message) && !mod.settingsHref) setEditing(mod)
    } finally {
      setToggling(null)
    }
  }

  function requestToggle(mod: Module, next: boolean) {
    if (mod.id === 'whitelist' && next) {
      setPendingWhitelist(mod)
      return
    }
    void toggle(mod, next)
  }

  if (loading && !data) {
    return (
      <>
        <PageHeader
          eyebrow="Configuration register"
          title="Modules"
          description="Control every Docket system connected to this server."
        />
        <ModulesSkeleton />
      </>
    )
  }
  if (error && !data) {
    return (
      <>
        <PageHeader eyebrow="Configuration" title="Modules" />
        <ErrorState onRetry={refetch} description={error} />
      </>
    )
  }

  return (
    <>
      <PageHeader
        eyebrow="Configuration register"
        title="Modules"
        description="Review the systems attached to this server, switch protection on, and tune how each module behaves."
        actions={
          <Badge tone="success" dot>
            {data?.enabledCount ?? 0} of {modules.length} online
          </Badge>
        }
      />

      <CoverageRegister modules={modules} />

      <div className="mb-5 mt-5 flex flex-col gap-3 border-y border-border bg-surface px-3 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative min-w-0 flex-1 sm:max-w-md">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-2" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search name, category, or module ID"
            className="h-9 rounded-md pl-9 pr-9"
            aria-label="Search modules"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="focus-ring absolute right-2 top-1/2 -translate-y-1/2 rounded-sm p-1 text-muted-2 hover:text-foreground"
              aria-label="Clear module search"
            >
              <X className="size-4" />
            </button>
          )}
        </div>
        <StatusFilters
          value={statusFilter}
          enabledCount={data?.enabledCount ?? 0}
          totalCount={modules.length}
          onChange={setStatusFilter}
        />
      </div>

      {error && (
        <div className="mb-4 flex items-center justify-between gap-3 border border-warning/30 bg-warning-soft px-3 py-2 text-sm text-warning" role="status">
          <span>Latest module state could not be refreshed: {error}</span>
          <Button variant="ghost" size="sm" onClick={refetch}>Retry</Button>
        </div>
      )}

      {filtered.length === 0 ? (
        <Card>
          <EmptyState
            icon={Search}
            title="No modules match this view"
            description="Clear the search or show every module to restore the register."
            action={
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setQuery('')
                  setStatusFilter('all')
                }}
              >
                Clear filters
              </Button>
            }
          />
        </Card>
      ) : (
        <div className="space-y-5" aria-live="polite">
          {grouped.map((group) => (
            <ModuleCategory
              key={group.category}
              category={group.category}
              modules={group.modules}
              allModules={group.allModules}
              canWrite={canWrite}
              toggling={toggling}
              editingId={editing?.id ?? null}
              onToggle={requestToggle}
              onOpenSettings={(mod) => setEditing((current) => current?.id === mod.id ? null : mod)}
              onCloseSettings={() => setEditing(null)}
              onSaved={() => {
                setEditing(null)
                void refetch()
              }}
            />
          ))}
        </div>
      )}

      <ConfirmDialog
        open={Boolean(pendingWhitelist)}
        onClose={() => setPendingWhitelist(null)}
        onConfirm={() => {
          const mod = pendingWhitelist
          setPendingWhitelist(null)
          if (mod) void toggle(mod, true)
        }}
        title="Enable strict whitelist mode?"
        description="New non-administrator members who are not on the allowlist will be removed when they join. Add trusted members before enabling it."
        confirmLabel="Enable whitelist"
        destructive
      />
    </>
  )
}

function CoverageRegister({ modules }: { modules: Module[] }) {
  return (
    <Card className="overflow-hidden rounded-lg border-border-strong shadow-none">
      <div className="grid md:grid-cols-[minmax(0,0.9fr)_minmax(0,1.35fr)]">
        <div className="border-b border-border bg-surface-2 p-5 md:border-b-0 md:border-r">
          <p className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.16em] text-accent">
            Live coverage map
          </p>
          <h2 className="mt-2 font-display text-xl font-semibold text-foreground">
            Every active system, on one register.
          </h2>
          <p className="mt-2 max-w-md text-sm leading-6 text-muted">
            Filled marks are running now. Empty marks are available but inactive or waiting for setup.
          </p>
        </div>
        <div className="divide-y divide-border bg-surface">
          {CATEGORY_ORDER.map((category) => {
            const categoryModules = modules.filter((mod) => mod.category === category)
            const enabled = categoryModules.filter((mod) => mod.enabled).length
            const meta = CATEGORY_META[category]
            return (
              <div key={category} className="grid grid-cols-[6.5rem_minmax(0,1fr)_auto] items-center gap-3 px-4 py-3.5 sm:grid-cols-[7.5rem_minmax(0,1fr)_auto]">
                <div>
                  <p className="font-mono text-[0.625rem] font-semibold uppercase tracking-[0.14em] text-muted-2">
                    {meta.registerId}
                  </p>
                  <p className="mt-0.5 text-sm font-medium text-foreground">{category}</p>
                </div>
                <div className="flex min-w-0 items-center gap-1.5" role="img" aria-label={`${enabled} of ${categoryModules.length} ${category.toLowerCase()} modules enabled`}>
                  {categoryModules.map((mod) => (
                    <span
                      key={mod.id}
                      title={`${mod.name}: ${mod.enabled ? 'enabled' : 'disabled'}`}
                      className={cn(
                        'h-2.5 min-w-3 flex-1 rounded-[2px] border transition-colors',
                        mod.enabled
                          ? 'border-accent bg-accent'
                          : 'border-border-strong bg-surface-2',
                      )}
                    />
                  ))}
                </div>
                <span className="w-10 text-right font-mono text-xs tabular-nums text-muted">
                  {enabled}/{categoryModules.length}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </Card>
  )
}

function StatusFilters({
  value,
  enabledCount,
  totalCount,
  onChange,
}: {
  value: StatusFilter
  enabledCount: number
  totalCount: number
  onChange: (value: StatusFilter) => void
}) {
  const filters: { value: StatusFilter; label: string; count: number }[] = [
    { value: 'all', label: 'All', count: totalCount },
    { value: 'enabled', label: 'Online', count: enabledCount },
    { value: 'disabled', label: 'Offline', count: totalCount - enabledCount },
  ]
  return (
    <div className="flex items-center gap-1" aria-label="Filter modules by status">
      {filters.map((filter) => (
        <button
          key={filter.value}
          type="button"
          aria-pressed={value === filter.value}
          onClick={() => onChange(filter.value)}
          className={cn(
            'focus-ring inline-flex h-8 items-center gap-1.5 rounded-md px-2.5 text-xs font-medium transition-colors',
            value === filter.value
              ? 'bg-accent text-accent-foreground'
              : 'text-muted hover:bg-surface-2 hover:text-foreground',
          )}
        >
          {filter.label}
          <span className={cn('font-mono text-[0.625rem] tabular-nums', value === filter.value ? 'opacity-75' : 'text-muted-2')}>
            {filter.count}
          </span>
        </button>
      ))}
    </div>
  )
}

function ModuleCategory({
  category,
  modules,
  allModules,
  canWrite,
  toggling,
  editingId,
  onToggle,
  onOpenSettings,
  onCloseSettings,
  onSaved,
}: {
  category: string
  modules: Module[]
  allModules: Module[]
  canWrite: boolean
  toggling: string | null
  editingId: string | null
  onToggle: (mod: Module, next: boolean) => void
  onOpenSettings: (mod: Module) => void
  onCloseSettings: () => void
  onSaved: () => void
}) {
  const headingId = `module-category-${category.toLowerCase()}`
  const meta = CATEGORY_META[category] ?? {
    description: 'Server systems and controls.',
    registerId: 'REG / SYS',
  }
  const enabled = allModules.filter((mod) => mod.enabled).length
  return (
    <section className="grid items-start gap-3 lg:grid-cols-[13rem_minmax(0,1fr)]" aria-labelledby={headingId}>
      <header className="px-1 py-2 lg:sticky lg:top-20">
        <p className="font-mono text-[0.625rem] font-semibold uppercase tracking-[0.15em] text-accent">
          {meta.registerId}
        </p>
        <h2 id={headingId} className="mt-1 font-display text-lg font-semibold text-foreground">
          {category}
        </h2>
        <p className="mt-1 text-xs leading-5 text-muted">{meta.description}</p>
        <p className="mt-3 font-mono text-[0.6875rem] tabular-nums text-muted-2">
          {enabled} online / {allModules.length} filed
        </p>
      </header>

      <Card className="overflow-hidden rounded-lg border-border-strong shadow-none">
        <ul className="divide-y divide-border">
          {modules.map((mod) => (
            <ModuleRow
              key={mod.id}
              mod={mod}
              canWrite={canWrite}
              toggling={toggling === mod.id}
              expanded={editingId === mod.id}
              onToggle={(next) => onToggle(mod, next)}
              onOpenSettings={() => onOpenSettings(mod)}
              onCloseSettings={onCloseSettings}
              onSaved={onSaved}
            />
          ))}
        </ul>
      </Card>
    </section>
  )
}

function ModuleRow({
  mod,
  canWrite,
  toggling,
  expanded,
  onToggle,
  onOpenSettings,
  onCloseSettings,
  onSaved,
}: {
  mod: Module
  canWrite: boolean
  toggling: boolean
  expanded: boolean
  onToggle: (next: boolean) => void
  onOpenSettings: () => void
  onCloseSettings: () => void
  onSaved: () => void
}) {
  const Icon = MODULE_ICONS[mod.id] ?? Blocks
  const hasSettings = mod.settingsHref || mod.special || mod.fields.length > 0
  const sheetId = `module-settings-${mod.id}`
  const status = toggling
    ? 'Updating'
    : mod.toggleable
      ? mod.enabled ? 'Enabled' : 'Disabled'
      : mod.id === 'moderation'
        ? 'Always on'
        : mod.enabled ? 'Configured' : 'Needs setup'
  const statusTone = mod.enabled ? 'text-success' : 'text-muted-2'
  return (
    <li className={cn('relative bg-surface', mod.enabled && 'rail rail-accent !pl-0')} data-enabled={mod.enabled}>
      <div className="grid gap-4 px-4 py-4 sm:px-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
        <div className="flex min-w-0 gap-3.5">
          <Icon className={cn('mt-0.5 size-5 shrink-0', mod.enabled ? 'text-accent' : 'text-muted-2')} aria-hidden />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="stamp">MOD / {mod.id.replaceAll('_', '-')}</span>
              <h3 className="font-display text-base font-semibold text-foreground">{mod.name}</h3>
              {mod.badge && <Badge tone={BADGE_TONE[mod.badge]}>{BADGE_LABEL[mod.badge]}</Badge>}
            </div>
            <p className="mt-1.5 max-w-3xl text-sm leading-6 text-muted">{mod.description}</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:pl-8 lg:justify-end lg:pl-0">
          <span className={cn('mr-1 inline-flex min-w-20 items-center gap-1.5 text-xs font-medium', statusTone)} aria-live="polite">
            {toggling ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : mod.enabled ? (
              <CheckCircle2 className="size-3.5" />
            ) : (
              <CircleOff className="size-3.5" />
            )}
            {status}
          </span>
          {mod.toggleable && (
            <Switch
              checked={mod.enabled}
              disabled={!canWrite || toggling}
              onChange={onToggle}
              label={`${mod.enabled ? 'Disable' : 'Enable'} ${mod.name}`}
            />
          )}
          {hasSettings && (
            mod.settingsHref ? (
              <Link
                href={mod.settingsHref}
                className={buttonVariants({ variant: 'secondary', size: 'sm' })}
              >
                Open Automod <ArrowUpRight className="size-3.5" />
              </Link>
            ) : (
              <Button
                variant={expanded ? 'subtle' : 'secondary'}
                size="sm"
                onClick={onOpenSettings}
                aria-expanded={expanded}
                aria-controls={sheetId}
              >
                <Settings2 className="size-3.5" /> {expanded ? 'Close' : 'Configure'}
              </Button>
            )
          )}
        </div>
      </div>
      {expanded && (
        <SettingsSheet
          id={sheetId}
          mod={mod}
          canWrite={canWrite}
          onClose={onCloseSettings}
          onSaved={onSaved}
        />
      )}
    </li>
  )
}

function ModulesSkeleton() {
  return (
    <div className="space-y-5" aria-label="Loading module register">
      <div className="skeleton h-40 w-full rounded-lg" />
      {[0, 1, 2].map((category) => (
        <div key={category} className="grid gap-3 lg:grid-cols-[13rem_minmax(0,1fr)]">
          <div className="space-y-2 px-1 py-2">
            <div className="skeleton h-3 w-20" />
            <div className="skeleton h-5 w-28" />
            <div className="skeleton h-3 w-40" />
          </div>
          <div className="overflow-hidden rounded-lg border border-border bg-surface">
            {[0, 1, 2].map((row) => (
              <div key={row} className="flex items-center gap-4 border-b border-border px-5 py-5 last:border-b-0">
                <div className="skeleton size-5" />
                <div className="flex-1 space-y-2">
                  <div className="skeleton h-4 w-36" />
                  <div className="skeleton h-3 w-2/3" />
                </div>
                <div className="skeleton h-8 w-24" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function SettingsSheet({
  id,
  mod,
  canWrite,
  onClose,
  onSaved,
}: {
  id: string
  mod: Module
  canWrite: boolean
  onClose: () => void
  onSaved: () => void
}) {
  const helper = mod.special ? FIELD_HELP[mod.special] : ''
  return (
    <div id={id} className="border-t border-border bg-surface-2 px-4 py-5 sm:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <p className="font-mono text-[0.625rem] font-semibold uppercase tracking-[0.15em] text-accent">
              Configuration sheet / {mod.id.replaceAll('_', '-')}
            </p>
            <h4 className="mt-1 font-display text-lg font-semibold text-foreground">{mod.name} settings</h4>
            <p className="mt-1 max-w-2xl text-sm text-muted">
              {helper || 'Update how this module behaves for the selected server.'}
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label={`Close ${mod.name} settings`}>
            <X className="size-4" /> Close
          </Button>
        </div>
        {mod.special === 'moderation' ? (
          <ModerationSheet mod={mod} canWrite={canWrite} onClose={onClose} onSaved={onSaved} />
        ) : mod.special === 'whitelist' ? (
          <WhitelistSheet mod={mod} canWrite={canWrite} onClose={onClose} onSaved={onSaved} />
        ) : mod.special ? (
          <OperationalModuleSheet mod={mod} canWrite={canWrite} onClose={onClose} onSaved={onSaved} />
        ) : (
          <FieldsSheet mod={mod} canWrite={canWrite} onClose={onClose} onSaved={onSaved} />
        )}
      </div>
    </div>
  )
}

const FIELD_HELP: Record<Module['special'] & string, string> = {
  moderation: 'Set the action policy, staff access, public responses, and warning escalation in one place.',
  aimod: 'Control how Docket interprets requests, gathers context, and confirms high-impact actions.',
  antiraid: 'Define the join signal, automatic response, quarantine path, and incident routing.',
  verification: 'Build the member verification path, including its roles, panel channel, logs, and voice gate.',
  whitelist: 'Choose rejection behavior and maintain the exact member allowlist enforced on join.',
  tickets: 'Route private support channels to the right category, staff role, and transcript log.',
  logging: 'Send each class of server event to a deliberate destination instead of one noisy catch-all channel.',
  welcome_card: 'Set the delivery channel and identity of the join card members see when they arrive.',
  autoroles: 'Choose the role Docket assigns to new human members when verification is not controlling access.',
}

type GuildResource = {
  id: string
  name: string
  position?: number
  type?: number
}

type GuildResourcesPayload = {
  roles: GuildResource[]
  channels: GuildResource[]
}

type ModerationFormValue = string | boolean | string[] | AutopunishRule[]
type ModerationForm = Record<string, ModerationFormValue>

const POLICY_KEYS = new Set([
  'moderation_dm_users',
  'moderation_use_timeouts',
  'moderation_delete_commands',
  'moderation_respond_with_reason',
  'moderation_preserve_ban_messages',
])

const RESPONSE_KEYS = new Set([
  'moderation_ban_response',
  'moderation_unban_response',
  'moderation_softban_response',
  'moderation_kick_response',
  'moderation_mute_response',
  'moderation_unmute_response',
])

function normalizeAutopunishRules(value: unknown): AutopunishRule[] {
  if (!Array.isArray(value)) return []
  const rules: AutopunishRule[] = []
  for (const candidate of value) {
    if (!candidate || typeof candidate !== 'object' || Array.isArray(candidate)) continue
    const raw = candidate as Record<string, unknown>
    if (!Number.isInteger(raw.warnings) || Number(raw.warnings) < 1 || Number(raw.warnings) > 100) continue
    if (raw.action !== 'timeout' && raw.action !== 'kick' && raw.action !== 'ban') continue
    const durationMinutes = raw.action === 'timeout' ? Number(raw.durationMinutes) : null
    if (raw.action === 'timeout' && (!Number.isInteger(durationMinutes) || Number(durationMinutes) < 1 || Number(durationMinutes) > 40320)) continue
    rules.push({
      warnings: Number(raw.warnings),
      action: raw.action,
      durationMinutes,
    })
  }
  return rules
    .filter((rule, index, all) => all.findIndex((candidate) => candidate.warnings === rule.warnings) === index)
    .sort((a, b) => a.warnings - b.warnings)
    .slice(0, 20)
}

function moderationInitialForm(mod: Module): ModerationForm {
  const initial: ModerationForm = {}
  for (const field of mod.fields) {
    const value = mod.values[field.key]
    if (field.key === 'moderation_use_timeouts') {
      initial[field.key] = true
    } else if (field.type === 'toggle') {
      initial[field.key] = Boolean(value)
    } else if (field.type === 'roleIds' || field.type === 'channelIds') {
      initial[field.key] = Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
    } else if (field.type === 'autopunishRules') {
      initial[field.key] = normalizeAutopunishRules(value)
    } else {
      initial[field.key] = value === null || value === undefined ? '' : String(value)
    }
  }
  return initial
}

function asStringList(value: ModerationFormValue | undefined): string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string') ? value : []
}

function asAutopunishRules(value: ModerationFormValue | undefined): AutopunishRule[] {
  return normalizeAutopunishRules(value)
}

function ModerationSheet({
  mod,
  canWrite,
  onClose,
  onSaved,
}: {
  mod: Module
  canWrite: boolean
  onClose: () => void
  onSaved: () => void
}) {
  const toast = useToast()
  const { data: resources, loading: resourcesLoading, error: resourcesError, refetch: refetchResources } =
    useApi<GuildResourcesPayload>('/api/guilds/resources')
  const initialForm = useMemo(() => moderationInitialForm(mod), [mod])
  const [form, setForm] = useState<ModerationForm>(initialForm)
  const [saving, setSaving] = useState(false)
  const dirty = JSON.stringify(form) !== JSON.stringify(initialForm)
  const roles = resources?.roles ?? []
  const channels = resources?.channels ?? []
  const policyFields = mod.fields.filter((field) => POLICY_KEYS.has(field.key))
  const responseFields = mod.fields.filter((field) => RESPONSE_KEYS.has(field.key))

  function update(key: string, value: ModerationFormValue) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  async function save() {
    if (!canWrite) return
    setSaving(true)
    try {
      const settings: Record<string, unknown> = {}
      for (const field of mod.fields) settings[field.key] = form[field.key]
      settings.moderation_use_timeouts = true
      const response = await fetch(`/api/modules/${mod.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings }),
      })
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body.error || 'Failed to save moderation settings')
      }
      toast.success('Moderation settings saved')
      onSaved()
    } catch (error) {
      toast.error('Save failed', error instanceof Error ? error.message : 'Try again in a moment.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        void save()
      }}
      className="space-y-5"
    >
      <ModerationSection
        register="ACTION / 01"
        title="Action behavior"
        description="Decide what members see and what remains in the channel when a moderator acts."
      >
        <div className="grid gap-2.5 md:grid-cols-2">
          {policyFields.map((field) => {
            const required = field.key === 'moderation_use_timeouts'
            return (
              <div
                key={field.key}
                className={cn(
                  'flex min-h-20 items-center justify-between gap-4 rounded-md border bg-surface px-3.5 py-3',
                  required ? 'border-accent-line' : 'border-border',
                )}
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <label htmlFor={`moderation-${field.key}`} className="text-sm font-medium text-foreground">
                      {field.label}
                    </label>
                    {required && <Badge tone="accent">New · Required</Badge>}
                  </div>
                  {field.hint && <p className="mt-1 text-xs leading-5 text-muted">{field.hint}</p>}
                </div>
                <Switch
                  id={`moderation-${field.key}`}
                  checked={required || Boolean(form[field.key])}
                  disabled={!canWrite || required}
                  onChange={(checked) => update(field.key, checked)}
                  label={field.label}
                />
              </div>
            )
          })}
        </div>
      </ModerationSection>

      <ModerationSection
        register="ROUTING / 02"
        title="Routing & immunity"
        description="Connect the channels Docket operates in and the roles that may—or may not—be acted on."
      >
        {resourcesError && (
          <div className="mb-4 flex flex-col gap-2 border border-warning/40 bg-warning-soft px-3 py-2.5 text-xs text-warning sm:flex-row sm:items-center sm:justify-between">
            <span>Discord channels and roles could not be refreshed. Existing selections are preserved.</span>
            <Button type="button" variant="ghost" size="sm" onClick={() => void refetchResources()}>
              Retry
            </Button>
          </div>
        )}
        <div className="grid gap-5 md:grid-cols-2">
          <SingleResourcePicker
            field={mod.fields.find((field) => field.key === 'mod_log_channel')!}
            resources={channels}
            value={String(form.mod_log_channel ?? '')}
            loading={resourcesLoading}
            disabled={!canWrite}
            kind="channel"
            onChange={(value) => update('mod_log_channel', value)}
          />
          <MultiResourcePicker
            field={mod.fields.find((field) => field.key === 'mod_roles')!}
            resources={roles}
            selected={asStringList(form.mod_roles)}
            loading={resourcesLoading}
            disabled={!canWrite}
            kind="role"
            onChange={(value) => update('mod_roles', value)}
          />
          <MultiResourcePicker
            field={mod.fields.find((field) => field.key === 'protected_roles')!}
            resources={roles}
            selected={asStringList(form.protected_roles)}
            loading={resourcesLoading}
            disabled={!canWrite}
            kind="role"
            onChange={(value) => update('protected_roles', value)}
          />
          <MultiResourcePicker
            field={mod.fields.find((field) => field.key === 'lockdown_channels')!}
            resources={channels}
            selected={asStringList(form.lockdown_channels)}
            loading={resourcesLoading}
            disabled={!canWrite}
            kind="channel"
            onChange={(value) => update('lockdown_channels', value)}
          />
        </div>
      </ModerationSection>

      <ModerationSection
        register="RESPONSE / 03"
        title="Custom responses"
        description="Set the public acknowledgement for each moderator action."
        badge="Standard"
      >
        <p className="mb-4 border-l-2 border-accent pl-3 text-xs leading-5 text-muted">
          Available variables: <code className="text-foreground">{'{user}'}</code>,{' '}
          <code className="text-foreground">{'{reason}'}</code>,{' '}
          <code className="text-foreground">{'{moderator}'}</code>, and{' '}
          <code className="text-foreground">{'{duration}'}</code>.
        </p>
        <div className="grid gap-4 md:grid-cols-2">
          {responseFields.map((field) => (
            <Field key={field.key} label={field.label} htmlFor={`moderation-${field.key}`}>
              <Input
                id={`moderation-${field.key}`}
                value={String(form[field.key] ?? '')}
                disabled={!canWrite}
                maxLength={field.maxLength ?? 500}
                autoComplete="off"
                onChange={(event) => update(field.key, event.target.value)}
              />
            </Field>
          ))}
        </div>
      </ModerationSection>

      <ModerationSection
        register="ESCALATION / 04"
        title="Autopunish"
        description="Apply one action when a member reaches an exact warning count."
      >
        <AutopunishBuilder
          rules={asAutopunishRules(form.moderation_autopunish_rules)}
          disabled={!canWrite}
          onChange={(rules) => update('moderation_autopunish_rules', rules)}
        />
      </ModerationSection>

      <div className="flex flex-col-reverse gap-2 border-t border-border pt-4 sm:flex-row sm:items-center sm:justify-end">
        {!canWrite && <p className="mr-auto text-xs text-muted">Your workspace role has read-only access.</p>}
        <Button type="button" variant="ghost" size="sm" onClick={onClose} disabled={saving}>
          Cancel
        </Button>
        <Button type="submit" size="sm" loading={saving} disabled={!canWrite || !dirty}>
          Save changes
        </Button>
      </div>
    </form>
  )
}

function ModerationSection({
  register,
  title,
  description,
  badge,
  children,
}: {
  register: string
  title: string
  description: string
  badge?: string
  children: React.ReactNode
}) {
  return (
    <section className="overflow-hidden rounded-lg border border-border bg-surface-2">
      <header className="flex flex-col gap-2 border-b border-border bg-surface px-4 py-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="font-mono text-[0.625rem] font-semibold uppercase tracking-[0.14em] text-accent">{register}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <h5 className="font-display text-base font-semibold text-foreground">{title}</h5>
            {badge && <Badge tone="info">{badge}</Badge>}
          </div>
          <p className="mt-1 text-xs leading-5 text-muted">{description}</p>
        </div>
      </header>
      <div className="p-4">{children}</div>
    </section>
  )
}

function resourceLabel(resource: GuildResource | undefined, id: string, kind: 'role' | 'channel'): string {
  if (!resource) return `Unknown ${kind} · ${id}`
  if (kind === 'role') return `@${resource.name}`
  if (resource.type === 4) return `Category · ${resource.name}`
  if (resource.type === 2) return `Voice · ${resource.name}`
  if (resource.type === 13) return `Stage · ${resource.name}`
  return `#${resource.name}`
}

function SingleResourcePicker({
  field,
  resources,
  value,
  loading,
  disabled,
  kind,
  onChange,
}: {
  field: ModuleField
  resources: GuildResource[]
  value: string
  loading: boolean
  disabled: boolean
  kind: 'role' | 'channel'
  onChange: (value: string) => void
}) {
  const options = [
    { label: 'Not configured', value: '' },
    ...resources.map((resource) => ({ label: resourceLabel(resource, resource.id, kind), value: resource.id })),
  ]
  if (value && !resources.some((resource) => resource.id === value)) {
    options.splice(1, 0, { label: resourceLabel(undefined, value, kind), value })
  }
  return (
    <Field label={field.label} htmlFor={`moderation-${field.key}`} hint={field.hint}>
      <Select
        id={`moderation-${field.key}`}
        value={value}
        disabled={disabled || loading}
        options={options}
        aria-label={field.label}
        onChange={(event) => onChange(event.target.value)}
      />
    </Field>
  )
}

function MultiResourcePicker({
  field,
  resources,
  selected,
  loading,
  disabled,
  kind,
  onChange,
}: {
  field: ModuleField
  resources: GuildResource[]
  selected: string[]
  loading: boolean
  disabled: boolean
  kind: 'role' | 'channel'
  onChange: (value: string[]) => void
}) {
  const [nextId, setNextId] = useState('')
  const available = resources.filter((resource) => !selected.includes(resource.id))
  const inputId = `moderation-${field.key}`

  function add(value: string) {
    if (!value || selected.includes(value)) return
    onChange([...selected, value])
    setNextId('')
  }

  return (
    <Field label={field.label} htmlFor={inputId} hint={field.hint}>
      <Select
        id={inputId}
        value={nextId}
        disabled={disabled || loading || available.length === 0}
        options={available.map((resource) => ({ label: resourceLabel(resource, resource.id, kind), value: resource.id }))}
        placeholder={loading ? `Loading ${kind}s…` : available.length === 0 ? `No more ${kind}s` : `Select ${kind}`}
        aria-label={`Add ${field.label.toLowerCase()}`}
        onChange={(event) => {
          setNextId(event.target.value)
          add(event.target.value)
        }}
      />
      {selected.length > 0 && (
        <ul className="flex flex-wrap gap-1.5" aria-label={`Selected ${field.label.toLowerCase()}`}>
          {selected.map((id) => {
            const resource = resources.find((candidate) => candidate.id === id)
            return (
              <li key={id} className="inline-flex max-w-full items-center gap-1.5 rounded-md border border-border bg-surface px-2 py-1 text-xs text-foreground">
                <span className="truncate">{resourceLabel(resource, id, kind)}</span>
                <button
                  type="button"
                  className="focus-ring rounded-sm text-muted-2 hover:text-danger disabled:pointer-events-none disabled:opacity-50"
                  disabled={disabled}
                  aria-label={`Remove ${resourceLabel(resource, id, kind)}`}
                  onClick={() => onChange(selected.filter((candidate) => candidate !== id))}
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

function AutopunishBuilder({
  rules,
  disabled,
  onChange,
}: {
  rules: AutopunishRule[]
  disabled: boolean
  onChange: (rules: AutopunishRule[]) => void
}) {
  const [warnings, setWarnings] = useState('3')
  const [action, setAction] = useState<AutopunishAction>('timeout')
  const [duration, setDuration] = useState('30')
  const [error, setError] = useState('')

  function addRule() {
    const warningCount = /^\d+$/.test(warnings.trim()) ? Number(warnings) : Number.NaN
    const durationMinutes = /^\d+$/.test(duration.trim()) ? Number(duration) : Number.NaN
    if (!Number.isInteger(warningCount) || warningCount < 1 || warningCount > 100) {
      setError('Warning count must be a whole number from 1 to 100.')
      return
    }
    if (rules.some((rule) => rule.warnings === warningCount)) {
      setError(`A rule already exists at ${warningCount} warnings. Remove it before adding a replacement.`)
      return
    }
    if (action === 'timeout' && (!Number.isInteger(durationMinutes) || durationMinutes < 1 || durationMinutes > 40320)) {
      setError('Timeout duration must be from 1 to 40,320 minutes (28 days).')
      return
    }
    if (rules.length >= 20) {
      setError('Autopunish supports up to 20 rules.')
      return
    }
    const nextRules = [
      ...rules,
      {
        warnings: warningCount,
        action,
        durationMinutes: action === 'timeout' ? durationMinutes : null,
      },
    ].sort((a, b) => a.warnings - b.warnings)
    const severity: Record<AutopunishAction, number> = { timeout: 0, kick: 1, ban: 2 }
    if (nextRules.some((rule, index) => index > 0 && severity[rule.action] < severity[nextRules[index - 1].action])) {
      setError('Actions must stay the same or become more severe as warning counts increase.')
      return
    }
    onChange(nextRules)
    setError('')
  }

  return (
    <div>
      <div className="grid items-end gap-3 rounded-md border border-border bg-surface p-3 sm:grid-cols-[7rem_minmax(10rem,1fr)_9rem_auto]">
        <Field label="Warning count" htmlFor="autopunish-warning-count">
          <Input
            id="autopunish-warning-count"
            type="number"
            inputMode="numeric"
            min={1}
            max={100}
            step={1}
            value={warnings}
            disabled={disabled}
            onChange={(event) => {
              setWarnings(event.target.value)
              setError('')
            }}
          />
        </Field>
        <Field label="Moderation action" htmlFor="autopunish-action">
          <Select
            id="autopunish-action"
            value={action}
            disabled={disabled}
            options={[
              { label: 'Timeout member', value: 'timeout' },
              { label: 'Kick member', value: 'kick' },
              { label: 'Ban member', value: 'ban' },
            ]}
            onChange={(event) => {
              setAction(event.target.value as AutopunishAction)
              setError('')
            }}
          />
        </Field>
        {action === 'timeout' ? (
          <Field label="Minutes" htmlFor="autopunish-duration">
            <Input
              id="autopunish-duration"
              type="number"
              inputMode="numeric"
              min={1}
              max={40320}
              step={1}
              value={duration}
              disabled={disabled}
              onChange={(event) => {
                setDuration(event.target.value)
                setError('')
              }}
            />
          </Field>
        ) : (
          <div className="flex h-10 items-center text-xs text-muted">No duration</div>
        )}
        <Button type="button" size="md" disabled={disabled || rules.length >= 20} onClick={addRule}>
          <Plus className="size-4" /> Add rule
        </Button>
      </div>
      <div className="mt-2 flex min-h-5 items-start justify-between gap-3 text-xs">
        <p className={error ? 'text-danger' : 'text-muted'} role={error ? 'alert' : undefined}>
          {error || 'Rules trigger once at the exact warning count. Discord timeouts can last up to 28 days.'}
        </p>
        <span className="shrink-0 font-mono text-muted-2">{rules.length} / 20</span>
      </div>

      <div className="mt-3 overflow-hidden rounded-md border border-border bg-surface">
        <div className="hidden grid-cols-[8rem_minmax(0,1fr)_10rem_2.5rem] gap-3 border-b border-border bg-surface-2 px-3 py-2 font-mono text-[0.625rem] font-semibold uppercase tracking-[0.12em] text-muted sm:grid">
          <span>Warning #</span>
          <span>Moderation</span>
          <span>Duration</span>
          <span className="sr-only">Actions</span>
        </div>
        {rules.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <p className="text-sm font-medium text-foreground">No automatic actions</p>
            <p className="mt-1 text-xs text-muted">Add a rule to act when a member reaches a warning count.</p>
          </div>
        ) : (
          <ol className="divide-y divide-border">
            {rules.map((rule) => (
              <li key={rule.warnings} className="grid gap-2 px-3 py-3 sm:grid-cols-[8rem_minmax(0,1fr)_10rem_2.5rem] sm:items-center sm:gap-3">
                <span className="font-mono text-xs font-semibold text-foreground">
                  {String(rule.warnings).padStart(2, '0')} warnings
                </span>
                <span className="text-sm capitalize text-foreground">{rule.action}</span>
                <span className="text-xs text-muted">
                  {rule.action === 'timeout' ? `${rule.durationMinutes} minutes` : 'Immediate'}
                </span>
                <button
                  type="button"
                  className="focus-ring justify-self-start rounded-md p-1.5 text-muted-2 transition-colors hover:bg-danger-soft hover:text-danger disabled:pointer-events-none disabled:opacity-50 sm:justify-self-end"
                  disabled={disabled}
                  aria-label={`Remove ${rule.action} at ${rule.warnings} warnings`}
                  onClick={() => onChange(rules.filter((candidate) => candidate.warnings !== rule.warnings))}
                >
                  <Trash2 className="size-4" />
                </button>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  )
}

type OperationalSpecial = Exclude<ModuleSpecial, 'moderation' | 'whitelist'>
type OperationalValue = string | boolean | string[]
type OperationalForm = Record<string, OperationalValue>

type OperationalSectionDefinition = {
  register: string
  title: string
  description: string
  keys: string[]
}

const OPERATIONAL_SECTIONS: Record<OperationalSpecial, OperationalSectionDefinition[]> = {
  aimod: [
    {
      register: 'SAFETY / 01',
      title: 'Decision guard',
      description: 'Control which high-impact requests pause for approval and how long that approval remains valid.',
      keys: ['aimod_confirm_enabled', 'aimod_confirm_timeout_seconds', 'aimod_confirm_actions'],
    },
    {
      register: 'CONTEXT / 02',
      title: 'Conversation context',
      description: 'Set how Docket talks and how much recent server context it may use for a decision.',
      keys: ['aimod_chat_enabled', 'aimod_context_messages', 'aimod_location_context'],
    },
    {
      register: 'PROVIDER / 03',
      title: 'Model routing',
      description: 'Keep the provider default for automatic upgrades, or pin an approved model identifier.',
      keys: ['aimod_model'],
    },
  ],
  antiraid: [
    {
      register: 'SIGNAL / 01',
      title: 'Raid signal',
      description: 'Define the join burst that Docket treats as coordinated activity and the response cooldown.',
      keys: ['antiraid_join_threshold', 'antiraid_join_seconds', 'antiraid_cooldown_seconds'],
    },
    {
      register: 'RESPONSE / 02',
      title: 'Containment path',
      description: 'Choose the immediate response, the policy for later joins, and the exact containment resources.',
      keys: ['antiraid_action', 'antiraid_raidmode_action', 'antiraid_quarantine_role', 'lockdown_channels'],
    },
    {
      register: 'INTEL / 03',
      title: 'Scoring & record',
      description: 'Tune optional AI scoring and route the finalized incident record to staff.',
      keys: ['antiraid_ai_enabled', 'antiraid_ai_min_confidence', 'antiraid_override_ai_action', 'antiraid_log_channel'],
    },
  ],
  verification: [
    {
      register: 'MEMBER / 01',
      title: 'Member path',
      description: 'Connect the waiting role, completion role, verification panel, and staff record.',
      keys: ['unverified_role', 'verified_role', 'verify_channel', 'verify_log_channel'],
    },
    {
      register: 'VOICE / 02',
      title: 'Voice gate',
      description: 'Optionally hold members in a voice waiting room with bypass roles and an expiry window.',
      keys: ['voice_verification_enabled', 'waiting_verify_voice_channel', 'vc_verify_bypass_roles', 'vc_verify_session_ttl'],
    },
  ],
  tickets: [
    {
      register: 'ROUTING / 01',
      title: 'Support routing',
      description: 'Choose where private tickets open, which team can respond, and where closure records land.',
      keys: ['ticket_category', 'ticket_support_role', 'ticket_log_channel'],
    },
  ],
  logging: [
    {
      register: 'ROUTES / 01',
      title: 'Event routing matrix',
      description: 'Give each high-volume event family its own destination. Leave a route blank to disable that stream.',
      keys: ['audit_log_channel', 'message_log_channel', 'voice_log_channel', 'automod_log_channel', 'report_log_channel', 'ticket_log_channel'],
    },
  ],
  welcome_card: [
    {
      register: 'DELIVERY / 01',
      title: 'Card delivery',
      description: 'Select the public channel that receives each new member card.',
      keys: ['welcome_channel'],
    },
    {
      register: 'IDENTITY / 02',
      title: 'Card identity',
      description: 'Set the server label, subtitle, and optional HTTPS background used by the renderer.',
      keys: ['welcome_server_name', 'welcome_system_name', 'welcome_bg_url'],
    },
  ],
  autoroles: [
    {
      register: 'ASSIGNMENT / 01',
      title: 'Join assignment',
      description: 'Choose the role granted to new human members when the verification module is not handling access.',
      keys: ['auto_role'],
    },
  ],
}

const OPERATIONAL_FLOW: Record<OperationalSpecial, [string, string, string]> = {
  aimod: ['Request', 'Safety check', 'Response or action'],
  antiraid: ['Join burst', 'Score & contain', 'Incident record'],
  verification: ['Member joins', 'Waiting gate', 'Verified access'],
  tickets: ['Member opens', 'Private support', 'Transcript logged'],
  logging: ['Server event', 'Classify stream', 'Route to channel'],
  welcome_card: ['Member joins', 'Render card', 'Post welcome'],
  autoroles: ['Human joins', 'Check verification', 'Assign role'],
}

function operationalInitialForm(mod: Module): OperationalForm {
  const initial: OperationalForm = {}
  for (const field of mod.fields) {
    const value = mod.values[field.key]
    if (field.type === 'toggle') {
      initial[field.key] = Boolean(value)
    } else if (field.type === 'roleIds' || field.type === 'channelIds' || field.type === 'multiSelect') {
      initial[field.key] = Array.isArray(value)
        ? value.filter((item): item is string => typeof item === 'string')
        : []
    } else {
      initial[field.key] = value === null || value === undefined ? '' : String(value)
    }
  }
  return initial
}

function OperationalModuleSheet({
  mod,
  canWrite,
  onClose,
  onSaved,
}: {
  mod: Module
  canWrite: boolean
  onClose: () => void
  onSaved: () => void
}) {
  const toast = useToast()
  const { data: resources, loading: resourcesLoading, error: resourcesError, refetch: refetchResources } =
    useApi<GuildResourcesPayload>('/api/guilds/resources')
  const initialForm = useMemo(() => operationalInitialForm(mod), [mod])
  const [form, setForm] = useState<OperationalForm>(initialForm)
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const special = mod.special as OperationalSpecial
  const sections = OPERATIONAL_SECTIONS[special]
  const dirty = JSON.stringify(form) !== JSON.stringify(initialForm)

  function update(key: string, value: OperationalValue) {
    setForm((current) => ({ ...current, [key]: value }))
    setErrors((current) => {
      if (!current[key]) return current
      const next = { ...current }
      delete next[key]
      return next
    })
  }

  async function save() {
    if (!canWrite) return
    const validationErrors = validateModuleForm(mod, form)
    setErrors(validationErrors)
    if (Object.keys(validationErrors).length > 0) {
      toast.warning('Check the highlighted settings', 'Every value must be valid before this module can be saved.')
      return
    }
    setSaving(true)
    try {
      const response = await fetch(`/api/modules/${mod.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: form }),
      })
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body.error || `Failed to save ${mod.name} settings`)
      }
      toast.success(`${mod.name} settings saved`)
      onSaved()
    } catch (error) {
      toast.error('Save failed', error instanceof Error ? error.message : 'Try again in a moment.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        void save()
      }}
      className="space-y-5"
    >
      <OperationalFlow special={special} form={form} fields={mod.fields} />

      {resourcesError && (
        <div className="flex flex-col gap-2 border border-warning/40 bg-warning-soft px-3 py-2.5 text-xs text-warning sm:flex-row sm:items-center sm:justify-between">
          <span>Discord channels and roles could not be refreshed. Existing selections are preserved.</span>
          <Button type="button" variant="ghost" size="sm" onClick={() => void refetchResources()}>
            Retry
          </Button>
        </div>
      )}

      {sections.map((section) => {
        const fields = section.keys
          .map((key) => mod.fields.find((field) => field.key === key))
          .filter((field): field is ModuleField => Boolean(field))
        if (fields.length === 0) return null
        return (
          <ModerationSection
            key={section.register}
            register={section.register}
            title={section.title}
            description={section.description}
          >
            <div className="grid gap-4 md:grid-cols-2">
              {fields.map((field) => (
                <OperationalField
                  key={field.key}
                  field={field}
                  value={form[field.key]}
                  resources={resources ?? { roles: [], channels: [] }}
                  resourcesLoading={resourcesLoading}
                  disabled={!canWrite}
                  error={errors[field.key]}
                  onChange={(value) => update(field.key, value)}
                />
              ))}
            </div>
          </ModerationSection>
        )
      })}

      <div className="flex flex-col-reverse gap-2 border-t border-border pt-4 sm:flex-row sm:items-center sm:justify-end">
        {!canWrite && <p className="mr-auto text-xs text-muted">Your workspace role has read-only access.</p>}
        <Button type="button" variant="ghost" size="sm" onClick={onClose} disabled={saving}>
          Cancel
        </Button>
        <Button type="submit" size="sm" loading={saving} disabled={!canWrite || !dirty}>
          Save changes
        </Button>
      </div>
    </form>
  )
}

function OperationalFlow({
  special,
  form,
  fields,
}: {
  special: OperationalSpecial
  form: OperationalForm
  fields: ModuleField[]
}) {
  const steps = OPERATIONAL_FLOW[special]
  const configured = fields.filter((field) => {
    const value = form[field.key]
    return Array.isArray(value) ? value.length > 0 : value !== '' && value !== false
  }).length
  const background = special === 'welcome_card' && typeof form.welcome_bg_url === 'string'
    && form.welcome_bg_url.startsWith('https://')
    ? form.welcome_bg_url
    : ''
  return (
    <div
      className="relative overflow-hidden rounded-lg border border-accent-line bg-surface px-4 py-4"
      style={background ? {
        backgroundImage: `linear-gradient(90deg, color-mix(in srgb, var(--surface) 96%, transparent), color-mix(in srgb, var(--surface) 78%, transparent)), url(${JSON.stringify(background)})`,
        backgroundPosition: 'center',
        backgroundSize: 'cover',
      } : undefined}
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="font-mono text-[0.625rem] font-semibold uppercase tracking-[0.14em] text-accent">Live workflow</p>
          <p className="mt-1 text-sm font-medium text-foreground">
            {configured} of {fields.length} controls configured
          </p>
          <p className="mt-1 text-xs leading-5 text-muted">Changes take effect from the bot settings store after this sheet is saved.</p>
        </div>
        <ol className="grid min-w-0 flex-1 grid-cols-3 border border-border bg-surface-2 lg:max-w-2xl">
          {steps.map((step, index) => (
            <li key={step} className="relative border-r border-border px-3 py-3 last:border-r-0">
              <span className="font-mono text-[0.625rem] text-muted-2">0{index + 1}</span>
              <p className="mt-1 text-xs font-medium leading-4 text-foreground">{step}</p>
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}

function OperationalField({
  field,
  value,
  resources,
  resourcesLoading,
  disabled,
  error,
  onChange,
}: {
  field: ModuleField
  value: OperationalValue | undefined
  resources: GuildResourcesPayload
  resourcesLoading: boolean
  disabled: boolean
  error?: string
  onChange: (value: OperationalValue) => void
}) {
  const fullWidth = field.type === 'toggle' || field.type === 'multiSelect' || field.type === 'roleIds' || field.type === 'channelIds'
  const fieldResources = field.type === 'roleId' || field.type === 'roleIds'
    ? resources.roles
    : resources.channels.filter((channel) => (field.channelTypes ?? [0, 5]).includes(channel.type ?? 0))

  if (field.type === 'roleId' || field.type === 'channelId') {
    const kind = field.type === 'roleId' ? 'role' : 'channel'
    return (
      <div className={cn(fullWidth && 'md:col-span-2')}>
        <SingleResourcePicker
          field={field}
          resources={fieldResources}
          value={typeof value === 'string' ? value : ''}
          loading={resourcesLoading}
          disabled={disabled}
          kind={kind}
          onChange={onChange}
        />
        {error && <p className="mt-1 text-xs text-danger">{error}</p>}
      </div>
    )
  }

  if (field.type === 'roleIds' || field.type === 'channelIds') {
    const kind = field.type === 'roleIds' ? 'role' : 'channel'
    return (
      <div className="md:col-span-2">
        <MultiResourcePicker
          field={field}
          resources={fieldResources}
          selected={Array.isArray(value) ? value : []}
          loading={resourcesLoading}
          disabled={disabled}
          kind={kind}
          onChange={onChange}
        />
        {error && <p className="mt-1 text-xs text-danger">{error}</p>}
      </div>
    )
  }

  if (field.type === 'multiSelect') {
    const selected = Array.isArray(value) ? value : []
    return (
      <fieldset className="md:col-span-2">
        <legend className="text-sm font-medium text-foreground">{field.label}</legend>
        {field.hint && <p className="mt-1 text-xs leading-5 text-muted">{field.hint}</p>}
        <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {(field.options ?? []).map((option) => {
            const checked = selected.includes(option.value)
            return (
              <button
                key={option.value}
                type="button"
                aria-pressed={checked}
                disabled={disabled}
                onClick={() => onChange(checked
                  ? selected.filter((candidate) => candidate !== option.value)
                  : [...selected, option.value])}
                className={cn(
                  'focus-ring flex min-h-10 items-center gap-2 rounded-md border px-3 py-2 text-left text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-60',
                  checked
                    ? 'border-accent-line bg-accent-soft text-foreground'
                    : 'border-border bg-surface text-muted hover:border-border-strong hover:text-foreground',
                )}
              >
                <CheckCircle2 className={cn('size-3.5 shrink-0', checked ? 'text-accent' : 'text-muted-2')} />
                {option.label}
              </button>
            )
          })}
        </div>
        {error && <p className="mt-1 text-xs text-danger">{error}</p>}
      </fieldset>
    )
  }

  return (
    <div className={cn(fullWidth && 'md:col-span-2')}>
      <FieldRow
        field={field}
        value={typeof value === 'boolean' ? value : String(value ?? '')}
        disabled={disabled}
        error={error}
        onChange={onChange}
      />
    </div>
  )
}

function FieldsSheet({
  mod,
  canWrite,
  onClose,
  onSaved,
}: {
  mod: Module
  canWrite: boolean
  onClose: () => void
  onSaved: () => void
}) {
  const toast = useToast()
  const initialForm = useMemo(() => {
    const initial: Record<string, string | boolean> = {}
    for (const f of mod.fields) {
      const v = mod.values[f.key]
      initial[f.key] = f.type === 'toggle' ? Boolean(v) : v === null || v === undefined ? '' : String(v)
    }
    return initial
  }, [mod])
  const [form, setForm] = useState<Record<string, string | boolean>>(initialForm)
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const dirty = mod.fields.some((field) => form[field.key] !== initialForm[field.key])

  async function save() {
    if (!canWrite) return
    const validationErrors = validateModuleForm(mod, form)
    setErrors(validationErrors)
    if (Object.keys(validationErrors).length > 0) {
      toast.warning('Check the highlighted settings', 'Every value must be valid before this module can be saved.')
      return
    }
    setSaving(true)
    try {
      const settings: Record<string, unknown> = {}
      for (const f of mod.fields) settings[f.key] = form[f.key]
      const res = await fetch(`/api/modules/${mod.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.error || 'Failed to save settings')
      }
      toast.success(`${mod.name} settings saved`)
      onSaved()
    } catch (e) {
      toast.error('Save failed', (e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        void save()
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        {mod.fields.length === 0 && (
          <p className="text-sm text-muted sm:col-span-2">This module has no adjustable settings yet.</p>
        )}
        {mod.fields.map((f) => (
          <div key={f.key} className={f.type === 'toggle' ? 'sm:col-span-2' : undefined}>
            <FieldRow
              field={f}
              value={form[f.key]}
              disabled={!canWrite}
              error={errors[f.key]}
              onChange={(value) => {
                setForm((current) => ({ ...current, [f.key]: value }))
                setErrors((current) => {
                  if (!current[f.key]) return current
                  const next = { ...current }
                  delete next[f.key]
                  return next
                })
              }}
            />
          </div>
        ))}
      </div>
      <div className="mt-5 flex flex-col-reverse gap-2 border-t border-border pt-4 sm:flex-row sm:items-center sm:justify-end">
        {!canWrite && <p className="mr-auto text-xs text-muted">Your workspace role has read-only access.</p>}
        <Button type="button" variant="ghost" size="sm" onClick={onClose} disabled={saving}>
          Cancel
        </Button>
        <Button type="submit" size="sm" loading={saving} disabled={!canWrite || !dirty}>
          Save changes
        </Button>
      </div>
    </form>
  )
}

function validateModuleForm(
  mod: Module,
  form: Record<string, string | boolean | string[]>,
): Record<string, string> {
  const errors: Record<string, string> = {}
  for (const field of mod.fields) {
    const value = form[field.key]
    if (field.type === 'toggle') continue
    if (field.type === 'roleIds' || field.type === 'channelIds') {
      if (!Array.isArray(value) || value.some((id) => !isDiscordSnowflake(id))) {
        errors[field.key] = `${field.label} must contain valid Discord resources`
      }
      continue
    }
    if (field.type === 'multiSelect') {
      const allowed = new Set(field.options?.map((option) => option.value) ?? [])
      if (!Array.isArray(value) || value.some((candidate) => !allowed.has(candidate))) {
        errors[field.key] = `${field.label} contains an unsupported option`
      }
      continue
    }
    const raw = String(value ?? '').trim()
    if (field.type === 'number') {
      if (!/^-?\d+$/.test(raw) || !Number.isSafeInteger(Number(raw))) {
        errors[field.key] = `${field.label} must be a whole number`
        continue
      }
      const number = Number(raw)
      if (field.min !== undefined && number < field.min) errors[field.key] = `${field.label} must be at least ${field.min}`
      if (field.max !== undefined && number > field.max) errors[field.key] = `${field.label} must be at most ${field.max}`
      continue
    }
    if ((field.type === 'roleId' || field.type === 'channelId') && raw && !isDiscordSnowflake(raw)) {
      errors[field.key] = `${field.label} must be a valid Discord ID or blank`
      continue
    }
    if (field.type === 'url' && raw) {
      try {
        const url = new URL(raw)
        if (url.protocol !== 'https:') throw new Error('HTTPS required')
      } catch {
        errors[field.key] = `${field.label} must be a valid HTTPS URL or blank`
      }
    }
    if (field.type === 'select' && field.options && !field.options.some((option) => option.value === raw)) {
      errors[field.key] = `Choose a valid ${field.label.toLowerCase()}`
    }
    if (raw.length > (field.maxLength ?? (field.type === 'url' ? 2048 : 200))) {
      errors[field.key] = `${field.label} is too long`
    }
  }
  return errors
}

function FieldRow({
  field,
  value,
  disabled,
  error,
  onChange,
}: {
  field: ModuleField
  value: string | boolean
  disabled: boolean
  error?: string
  onChange: (v: string | boolean) => void
}) {
  const inputId = `module-field-${field.key}`
  if (field.type === 'toggle') {
    return (
      <div className="flex items-center justify-between gap-4 rounded-lg border border-border bg-surface px-3 py-2.5">
        <div>
          <label htmlFor={inputId} className="text-sm font-medium text-foreground">{field.label}</label>
          {field.hint && <p className="text-xs text-muted">{field.hint}</p>}
        </div>
        <Switch id={inputId} checked={Boolean(value)} disabled={disabled} onChange={onChange} label={field.label} />
      </div>
    )
  }
  if (field.type === 'select' && field.options) {
    return (
      <Field label={field.label} htmlFor={inputId} hint={field.hint} error={error}>
        <Select
          id={inputId}
          value={String(value)}
          disabled={disabled}
          options={field.options}
          aria-invalid={Boolean(error)}
          onChange={(e) => onChange(e.target.value)}
        />
      </Field>
    )
  }
  const inputMode = field.type === 'number' ? 'numeric' : field.type === 'url' ? 'url' : 'text'
  const placeholder =
    field.placeholder ??
    (field.type === 'roleId'
      ? 'Discord role ID'
      : field.type === 'channelId'
        ? 'Discord channel ID'
        : field.type === 'roleIds'
          ? 'Comma-separated role IDs'
          : undefined)
  return (
    <Field label={field.label} htmlFor={inputId} hint={field.hint} error={error}>
      <Input
        id={inputId}
        type={field.type === 'number' ? 'number' : field.type === 'url' ? 'url' : 'text'}
        value={String(value)}
        disabled={disabled}
        min={field.min}
        max={field.max}
        step={field.type === 'number' ? 1 : undefined}
        maxLength={field.maxLength ?? (field.type === 'url' ? 2048 : field.type === 'text' ? 200 : undefined)}
        inputMode={inputMode}
        placeholder={placeholder}
        aria-invalid={Boolean(error)}
        autoComplete="off"
        onChange={(e) => onChange(e.target.value)}
      />
    </Field>
  )
}

// ---------------------------------------------------------------------------
// Whitelist member list with add/remove and non-whitelisted behavior note.
// ---------------------------------------------------------------------------

type WhitelistEntry = { userId: string; addedBy: string | null; createdAt: string | null }

function WhitelistSheet({
  mod,
  canWrite,
  onClose,
  onSaved,
}: {
  mod: Module
  canWrite: boolean
  onClose: () => void
  onSaved: () => void
}) {
  const toast = useToast()
  const { data, loading, error, refetch } = useApi<{ data: WhitelistEntry[] }>('/api/modules/whitelist')
  const [newId, setNewId] = useState('')
  const [busy, setBusy] = useState(false)
  const initialPolicy = useMemo(() => ({
    whitelist_immunity: Boolean(mod.values.whitelist_immunity),
    whitelist_dm_join: Boolean(mod.values.whitelist_dm_join),
  }), [mod])
  const [policy, setPolicy] = useState(initialPolicy)
  const entries = data?.data ?? []
  const policyDirty = JSON.stringify(policy) !== JSON.stringify(initialPolicy)

  async function mutate(method: 'POST' | 'DELETE', userId: string) {
    if (!canWrite) return
    setBusy(true)
    try {
      const res = await fetch('/api/modules/whitelist', {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId }),
      })
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || 'Request failed')
      if (method === 'POST') setNewId('')
      toast.success(method === 'POST' ? 'Added to whitelist' : 'Removed from whitelist')
      await refetch()
    } catch (e) {
      toast.error('Whitelist update failed', (e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function savePolicy() {
    if (!canWrite) return
    setBusy(true)
    try {
      const response = await fetch('/api/modules/whitelist', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: policy }),
      })
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body.error || 'Failed to save whitelist behavior')
      }
      toast.success('Whitelist behavior saved')
      onSaved()
    } catch (error) {
      toast.error('Save failed', error instanceof Error ? error.message : 'Try again in a moment.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5">
      <ModerationSection
        register="BEHAVIOR / 01"
        title="Rejection policy"
        description="Choose who may bypass the register and whether rejected members receive an explanation."
      >
        <div className="grid gap-2.5 md:grid-cols-2">
          {mod.fields.map((field) => (
            <div key={field.key} className="flex min-h-20 items-center justify-between gap-4 rounded-md border border-border bg-surface px-3.5 py-3">
              <div className="min-w-0">
                <label htmlFor={`whitelist-${field.key}`} className="text-sm font-medium text-foreground">{field.label}</label>
                {field.hint && <p className="mt-1 text-xs leading-5 text-muted">{field.hint}</p>}
              </div>
              <Switch
                id={`whitelist-${field.key}`}
                checked={Boolean(policy[field.key as keyof typeof policy])}
                disabled={!canWrite || busy}
                label={field.label}
                onChange={(checked) => setPolicy((current) => ({ ...current, [field.key]: checked }))}
              />
            </div>
          ))}
        </div>
      </ModerationSection>

      <ModerationSection
        register="REGISTER / 02"
        title="Approved members"
        description="Pre-approve Discord user IDs before they join, or remove access from the current register."
      >
      <div
        className={cn(
          'mb-4 border p-3 text-xs leading-relaxed',
          mod.enabled
            ? 'border-danger/40 bg-danger-soft text-danger'
            : 'border-border bg-surface-2 text-muted',
        )}
      >
        {mod.enabled ? (
          <>
            <span className="font-semibold">Strict mode is ON.</span> New non-administrator members
            who are not on this list are <span className="font-semibold">removed when they join</span>.
            Administrators remain exempt while administrator immunity is enabled above.
          </>
        ) : (
          <>
            Strict mode is off. Anyone can join. Turn the Whitelist module on to start removing
            non-whitelisted members on join.
          </>
        )}
      </div>

      {canWrite && (
        <div className="mb-4 flex flex-col items-stretch gap-2 sm:flex-row sm:items-end">
          <Field label="Add a member by user ID" htmlFor="whitelist-member-id" className="flex-1">
            <Input
              id="whitelist-member-id"
              value={newId}
              inputMode="numeric"
              placeholder="Discord user ID"
              disabled={busy}
              aria-invalid={Boolean(newId.trim()) && !isDiscordSnowflake(newId.trim())}
              onChange={(e) => setNewId(e.target.value)}
            />
          </Field>
          <Button
            size="md"
            className="gap-1.5"
            disabled={busy || !isDiscordSnowflake(newId.trim())}
            onClick={() => mutate('POST', newId.trim())}
          >
            <Plus className="size-4" /> Add
          </Button>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="size-5 animate-spin text-muted" aria-label="Loading whitelist" />
        </div>
      ) : error ? (
        <ErrorState onRetry={refetch} description={error} />
      ) : entries.length === 0 ? (
        <EmptyState title="No one is whitelisted yet" description="Add a member above." />
      ) : (
        <ul className="max-h-72 divide-y divide-border overflow-y-auto border border-border bg-surface">
          {entries.map((e) => (
            <li
              key={e.userId}
              className="flex items-center justify-between gap-3 px-3 py-2.5"
            >
              <span className="font-mono text-xs text-foreground">{e.userId}</span>
              {canWrite && (
                <button
                  type="button"
                  className="focus-ring rounded-md p-1 text-muted-2 transition-colors hover:text-danger"
                  disabled={busy}
                  aria-label={`Remove ${e.userId}`}
                  onClick={() => mutate('DELETE', e.userId)}
                >
                  <Trash2 className="size-4" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      </ModerationSection>

      <div className="flex flex-col-reverse gap-2 border-t border-border pt-4 sm:flex-row sm:items-center sm:justify-end">
        {!canWrite && <p className="mr-auto text-xs text-muted">Your workspace role has read-only access.</p>}
        <Button type="button" variant="ghost" size="sm" onClick={onClose} disabled={busy}>
          Cancel
        </Button>
        <Button type="button" size="sm" loading={busy && policyDirty} disabled={!canWrite || !policyDirty || busy} onClick={() => void savePolicy()}>
          Save behavior
        </Button>
      </div>
    </div>
  )
}
