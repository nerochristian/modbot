'use client'

import { useState } from 'react'
import { Hash, Shield, AlertTriangle, Save } from 'lucide-react'
import { SettingsCard } from '@/components/dashboard/setting-section'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Input, Field } from '@/components/ui/input'
import { useToast } from '@/components/ui/toast'
import { useApi } from '@/lib/use-api'

type ServerSettings = {
  prefix: string
  deleteCommandMessages: boolean
  warnEnabled: boolean
  warnMuteAt: number
  warnKickAt: number
  warnBanAt: number
  warnMuteDuration: number
  dmUsers: boolean
  respondWithReason: boolean
  preserveBanMessages: boolean
  useTimeouts: boolean
}

export default function ServerSettingsPage() {
  const toast = useToast()
  const { data, loading, error, refetch } = useApi<{ settings: ServerSettings }>('/api/settings/server')
  const [busy, setBusy] = useState(false)
  const [draft, setDraft] = useState<ServerSettings | null>(null)

  async function save() {
    if (!draft) return
    setBusy(true)
    try {
      const res = await fetch('/api/settings/server', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prefix: draft.prefix,
          deleteCommandMessages: draft.deleteCommandMessages,
          warnEnabled: draft.warnEnabled,
          warnMuteAt: draft.warnMuteAt,
          warnKickAt: draft.warnKickAt,
          warnBanAt: draft.warnBanAt,
          warnMuteDuration: draft.warnMuteDuration,
          dmUsers: draft.dmUsers,
          respondWithReason: draft.respondWithReason,
          preserveBanMessages: draft.preserveBanMessages,
          useTimeouts: draft.useTimeouts,
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body.error ?? 'Could not save server settings.')
      refetch()
      toast.success('Server settings saved')
    } catch (err) {
      toast.error('Could not save server settings', err instanceof Error ? err.message : 'Try again in a moment.')
    } finally {
      setBusy(false)
    }
  }

  if (error && !data) {
    return (
      <SettingsCard title="Server settings" description="Manage your server configuration.">
        <p className="text-sm text-danger">{error}</p>
      </SettingsCard>
    )
  }

  if (loading || !draft) {
    return (
      <SettingsCard title="Server settings" description="Manage your server configuration.">
        <div className="space-y-3">
          <div className="h-6 w-48 animate-pulse rounded-md bg-surface-2" />
          <div className="h-4 w-full animate-pulse rounded-md bg-surface-2" />
          <div className="h-4 w-3/4 animate-pulse rounded-md bg-surface-2" />
        </div>
      </SettingsCard>
    )
  }

  return (
    <>
      <SettingsCard
        title="Server settings"
        description="Manage your server prefix, moderation behavior, and warning thresholds."
        footer={
          <Button onClick={save} loading={busy}>
            <Save className="size-4" />
            Save changes
          </Button>
        }
      >
        <div className="space-y-8">
          {/* Server prefix */}
          <section>
            <div className="flex items-center gap-2 mb-2">
              <Hash className="size-4 text-muted" />
              <h3 className="text-sm font-medium text-foreground">Server prefix</h3>
            </div>
            <p className="text-xs text-muted mb-3">
              The prefix used to invoke moderation commands. Defaults to &lt;code&gt;,&lt;/code&gt;. Only single-character or short prefixes are recommended.
            </p>
            <Field label="Command prefix">
              <Input
                value={draft.prefix}
                onChange={(e) => setDraft({ ...draft, prefix: e.target.value })}
                placeholder=","
                maxLength={5}
              />
            </Field>
          </section>

          {/* Moderation behavior */}
          <section>
            <div className="flex items-center gap-2 mb-2">
              <Shield className="size-4 text-muted" />
              <h3 className="text-sm font-medium text-foreground">Moderation behavior</h3>
            </div>
            <p className="text-xs text-muted mb-4">
              Control how the bot handles moderation commands and user communication.
            </p>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Delete command messages</p>
                  <p className="text-xs text-muted">Remove the command message after executing moderation commands.</p>
                </div>
                <Switch
                  checked={draft.deleteCommandMessages}
                  onChange={(v) => setDraft({ ...draft, deleteCommandMessages: v })}
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">DM users on moderation action</p>
                  <p className="text-xs text-muted">Send a DM to the user when a moderation action is taken.</p>
                </div>
                <Switch
                  checked={draft.dmUsers}
                  onChange={(v) => setDraft({ ...draft, dmUsers: v })}
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Respond with reason</p>
                  <p className="text-xs text-muted">Include the reason in the bot&apos;s response to moderation commands.</p>
                </div>
                <Switch
                  checked={draft.respondWithReason}
                  onChange={(v) => setDraft({ ...draft, respondWithReason: v })}
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Preserve ban messages</p>
                  <p className="text-xs text-muted">Keep ban messages visible in the channel after the user is banned.</p>
                </div>
                <Switch
                  checked={draft.preserveBanMessages}
                  onChange={(v) => setDraft({ ...draft, preserveBanMessages: v })}
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Use timeouts</p>
                  <p className="text-xs text-muted">Use Discord timeouts instead of temporary bans when available.</p>
                </div>
                <Switch
                  checked={draft.useTimeouts}
                  onChange={(v) => setDraft({ ...draft, useTimeouts: v })}
                />
              </div>
            </div>
          </section>

          {/* Warning thresholds */}
          <section>
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="size-4 text-muted" />
              <h3 className="text-sm font-medium text-foreground">Warning thresholds</h3>
            </div>
            <p className="text-xs text-muted mb-4">
              Automatically escalate moderation actions based on the number of warnings a user has received.
            </p>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Enable warning thresholds</p>
                  <p className="text-xs text-muted">Turn on automatic escalation based on warning count.</p>
                </div>
                <Switch
                  checked={draft.warnEnabled}
                  onChange={(v) => setDraft({ ...draft, warnEnabled: v })}
                />
              </div>
              {draft.warnEnabled && (
                <div className="space-y-4 pl-2 border-l border-border">
                  <Field label="Mute at" hint="Number of warnings before muting the user">
                    <Input
                      type="number"
                      min={1}
                      max={20}
                      value={draft.warnMuteAt}
                      onChange={(e) => setDraft({ ...draft, warnMuteAt: Math.max(1, Math.min(20, parseInt(e.target.value) || 1)) })}
                    />
                  </Field>
                  <Field label="Kick at" hint="Number of warnings before kicking the user">
                    <Input
                      type="number"
                      min={1}
                      max={20}
                      value={draft.warnKickAt}
                      onChange={(e) => setDraft({ ...draft, warnKickAt: Math.max(1, Math.min(20, parseInt(e.target.value) || 1)) })}
                    />
                  </Field>
                  <Field label="Ban at" hint="Number of warnings before banning the user">
                    <Input
                      type="number"
                      min={1}
                      max={20}
                      value={draft.warnBanAt}
                      onChange={(e) => setDraft({ ...draft, warnBanAt: Math.max(1, Math.min(20, parseInt(e.target.value) || 1)) })}
                    />
                  </Field>
                  <Field label="Mute duration (seconds)" hint="How long the mute lasts">
                    <Input
                      type="number"
                      min={60}
                      max={2592000}
                      value={draft.warnMuteDuration}
                      onChange={(e) => setDraft({ ...draft, warnMuteDuration: Math.max(60, Math.min(2592000, parseInt(e.target.value) || 60)) })}
                    />
                  </Field>
                </div>
              )}
            </div>
          </section>
        </div>
      </SettingsCard>
    </>
  )
}
