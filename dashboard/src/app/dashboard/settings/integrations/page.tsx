'use client'

import { useState } from 'react'
import { Copy, RefreshCw, Check, MessageSquare, GitBranch, Mail, Webhook } from 'lucide-react'
import { SettingsCard, SettingRow } from '@/components/dashboard/setting-section'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/components/ui/toast'

function makeKey() {
  const rand = Array.from(crypto.getRandomValues(new Uint8Array(24)))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
  return `sk_live_${rand}`
}

const INTEGRATIONS = [
  { key: 'slack', name: 'Slack', description: 'Send alerts and reports to channels.', icon: MessageSquare, connected: true },
  { key: 'github', name: 'GitHub', description: 'Link deploys to activity events.', icon: GitBranch, connected: false },
  { key: 'email', name: 'Email digests', description: 'Weekly summaries to your inbox.', icon: Mail, connected: true },
  { key: 'webhook', name: 'Webhooks', description: 'POST events to your own endpoint.', icon: Webhook, connected: false },
]

export default function IntegrationsSettingsPage() {
  const toast = useToast()
  const [apiKey, setApiKey] = useState(makeKey())
  const [copied, setCopied] = useState(false)
  const [connections, setConnections] = useState(
    Object.fromEntries(INTEGRATIONS.map((i) => [i.key, i.connected])),
  )

  async function copy() {
    try {
      await navigator.clipboard.writeText(apiKey)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      toast.error('Could not copy to clipboard')
    }
  }

  function regenerate() {
    setApiKey(makeKey())
    toast.success('New API key generated', 'Update your integrations with the new key.')
  }

  return (
    <>
      <SettingsCard
        title="API keys"
        description="Use these keys to authenticate requests to the Nebula API."
        footer={
          <Button variant="outline" onClick={regenerate}>
            <RefreshCw className="size-4" />
            Regenerate key
          </Button>
        }
      >
        <div className="flex items-center gap-2 rounded-lg border border-border bg-surface-2 p-1 pl-3">
          <code className="flex-1 truncate font-mono text-sm text-foreground">{apiKey}</code>
          <Button variant="secondary" size="sm" onClick={copy}>
            {copied ? <Check className="size-4 text-success" /> : <Copy className="size-4" />}
            {copied ? 'Copied' : 'Copy'}
          </Button>
        </div>
        <p className="mt-2 text-xs text-muted">
          Keep this secret. Regenerating immediately invalidates the previous key.
        </p>
      </SettingsCard>

      <SettingsCard title="Connected services" description="Manage integrations with your favorite tools.">
        <div className="divide-y divide-border">
          {INTEGRATIONS.map((i) => (
            <SettingRow key={i.key} label={i.name} description={i.description}>
              <div className="flex items-center gap-3">
                <span className="flex size-9 items-center justify-center rounded-lg bg-surface-2 text-foreground">
                  <i.icon className="size-4.5" />
                </span>
                <Badge tone={connections[i.key] ? 'success' : 'neutral'}>
                  {connections[i.key] ? 'Connected' : 'Not connected'}
                </Badge>
                <Switch
                  checked={connections[i.key]}
                  onChange={(v) => {
                    setConnections((c) => ({ ...c, [i.key]: v }))
                    toast.success(`${i.name} ${v ? 'connected' : 'disconnected'}`)
                  }}
                  label={`Toggle ${i.name}`}
                />
              </div>
            </SettingRow>
          ))}
        </div>
      </SettingsCard>
    </>
  )
}
