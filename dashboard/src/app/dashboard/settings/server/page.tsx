'use client'

import { useEffect, useState } from 'react'
import { Check } from 'lucide-react'
import { SettingsCard, SettingRow } from '@/components/dashboard/setting-section'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorState } from '@/components/ui/empty-state'
import { useToast } from '@/components/ui/toast'
import { cn } from '@/lib/utils'

type ServerSettings = {
  prefix: string
  deleteCommandMessages: boolean
}

const PRESET_PREFIXES = [',', '!', '.', '?', '$', ';', '+', '~']

async function fetchSettings(): Promise<ServerSettings> {
  const res = await fetch('/api/settings/server', { cache: 'no-store' })
  const body = await res.json().catch(() => ({}))
  if (!res.ok || !body.settings) throw new Error(body.error ?? 'Server settings are unavailable.')
  return body.settings as ServerSettings
}

function validatePrefix(value: string): string | null {
  const trimmed = value.trim()
  if (trimmed.length === 0) return 'Prefix cannot be empty.'
  if (trimmed.length > 5) return 'Prefix must be 5 characters or fewer.'
  if (/\s/.test(trimmed)) return 'Prefix cannot contain spaces.'
  if (/^<[@#&!]/.test(trimmed)) return 'Prefix cannot be a Discord mention or emoji format.'
  return null
}

export default function ServerSettingsPage() {
  const toast = useToast()
  const [settings, setSettings] = useState<ServerSettings | null>(null)
  const [prefixDraft, setPrefixDraft] = useState('')
  const [deleteDraft, setDeleteDraft] = useState(false)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    setLoading(true)
    setLoadError('')
    try {
      const data = await fetchSettings()
      setSettings(data)
      setPrefixDraft(data.prefix)
      setDeleteDraft(data.deleteCommandMessages)
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Server settings are unavailable.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    void fetchSettings()
      .then((data) => {
        if (cancelled) return
        setSettings(data)
        setPrefixDraft(data.prefix)
        setDeleteDraft(data.deleteCommandMessages)
      })
      .catch((error: unknown) => {
        if (!cancelled) setLoadError(error instanceof Error ? error.message : 'Server settings are unavailable.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const prefixError = validatePrefix(prefixDraft)
  const prefixChanged = settings !== null && prefixDraft.trim() !== settings.prefix
  const deleteChanged = settings !== null && deleteDraft !== settings.deleteCommandMessages
  const hasChanges = prefixChanged || deleteChanged
  const canSave = hasChanges && !prefixError && !busy

  async function save() {
    if (!canSave) return
    setBusy(true)
    try {
      const patch: { prefix?: string; deleteCommandMessages?: boolean } = {}
      if (prefixChanged) patch.prefix = prefixDraft.trim()
      if (deleteChanged) patch.deleteCommandMessages = deleteDraft
      const res = await fetch('/api/settings/server', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error ?? 'Could not save server settings.')
      const next = body.settings as ServerSettings
      setSettings(next)
      setPrefixDraft(next.prefix)
      setDeleteDraft(next.deleteCommandMessages)
      toast.success('Server settings saved', 'Changes apply within a few minutes.')
    } catch (error) {
      toast.error('Could not save settings', error instanceof Error ? error.message : undefined)
    } finally {
      setBusy(false)
    }
  }

  if (loadError && !settings) {
    return (
      <SettingsCard title="Server" description="Core bot configuration for this server.">
        <ErrorState description={loadError} onRetry={load} />
      </SettingsCard>
    )
  }

  if (loading || !settings) {
    return (
      <SettingsCard title="Server" description="Core bot configuration for this server.">
        <div className="space-y-4">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      </SettingsCard>
    )
  }

  return (
    <SettingsCard
      title="Server"
      description="Core bot configuration for this server. Changes apply within a few minutes."
      footer={
        <Button onClick={save} loading={busy} disabled={!canSave}>
          Save changes
        </Button>
      }
    >
      <div className="divide-y divide-border">
        <SettingRow
          label="Command prefix"
          description="The character(s) that trigger text commands. Slash commands always work regardless of prefix."
          htmlFor="prefix-input"
        >
          <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row sm:items-center">
            <div className="flex flex-wrap gap-1.5">
              {PRESET_PREFIXES.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPrefixDraft(p)}
                  className={cn(
                    'focus-ring grid size-9 place-items-center rounded-lg border font-mono text-sm font-semibold transition-colors',
                    prefixDraft.trim() === p
                      ? 'border-accent bg-accent-soft text-accent'
                      : 'border-border bg-surface text-foreground hover:border-border-strong',
                  )}
                >
                  {prefixDraft.trim() === p ? <Check className="size-4" /> : p}
                </button>
              ))}
            </div>
            <Input
              id="prefix-input"
              value={prefixDraft}
              onChange={(e) => setPrefixDraft(e.target.value)}
              maxLength={5}
              className="w-28 font-mono"
              placeholder="custom"
              aria-label="Custom prefix"
            />
          </div>
        </SettingRow>

        {prefixError && (
          <p className="-mt-2 text-xs text-danger">{prefixError}</p>
        )}

        <SettingRow
          label="Delete command messages"
          description="When enabled, the bot deletes your message after a moderation command runs. Off by default."
        >
          <Switch
            checked={deleteDraft}
            onChange={setDeleteDraft}
            label="Delete command messages"
          />
        </SettingRow>
      </div>

      <div className="mt-6 rounded-xl border border-border bg-surface-2/40 p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-2">Preview</p>
        <p className="mt-2 font-mono text-sm text-foreground">
          {prefixDraft.trim() || ','}help · {prefixDraft.trim() || ','}ban @user · {prefixDraft.trim() || ','}purge 50
        </p>
      </div>
    </SettingsCard>
  )
}
