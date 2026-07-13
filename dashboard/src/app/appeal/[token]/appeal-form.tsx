'use client'

import { useState } from 'react'
import { CheckCircle2, FileWarning } from 'lucide-react'
import { Badge, statusTone } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Textarea } from '@/components/ui/input'

type AppealCase = {
  ref: number
  action: string
  reason: string
  status: string
  createdAt: string
  expiresAt: string
}

export function AppealForm({ token, moderationCase }: { token: string; moderationCase: AppealCase }) {
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [receipt, setReceipt] = useState<number | null>(null)

  async function submit() {
    setBusy(true)
    setError('')
    try {
      const response = await fetch(`/api/appeals/public/${encodeURIComponent(token)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      })
      const body = await response.json().catch(() => ({}))
      if (!response.ok) {
        setError(body.issues?.[0]?.message ?? body.error ?? 'The appeal could not be submitted.')
        return
      }
      setReceipt(Number(body.ref))
    } catch {
      setError('The appeal service could not be reached. Check your connection and try again.')
    } finally {
      setBusy(false)
    }
  }

  if (receipt !== null) {
    return (
      <Card className="border-success/30">
        <CardContent className="py-10 text-center">
          <CheckCircle2 className="mx-auto size-9 text-success" />
          <h1 className="mt-4 font-display text-2xl font-semibold text-foreground">Appeal submitted</h1>
          <p className="mt-2 text-sm text-muted">
            Your appeal reference is <span className="font-mono font-semibold text-foreground">APL-{String(receipt).padStart(4, '0')}</span>.
            The server moderation team can now review it.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="grid size-10 place-items-center rounded-lg bg-danger-soft text-danger">
                <FileWarning className="size-5" />
              </span>
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.12em] text-muted">Case</p>
                <h1 className="font-display text-xl font-semibold text-foreground">CASE-{String(moderationCase.ref).padStart(4, '0')}</h1>
              </div>
            </div>
            <div className="flex gap-2">
              <Badge tone={statusTone(moderationCase.action)}>{moderationCase.action}</Badge>
              <Badge tone={statusTone(moderationCase.status)}>{moderationCase.status}</Badge>
            </div>
          </div>
          <div className="rounded-lg border border-border bg-surface-2 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted">Recorded reason</p>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-foreground">{moderationCase.reason}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <label htmlFor="appeal-message" className="text-sm font-semibold text-foreground">Why should this case be reviewed?</label>
          <p className="mt-1 text-sm text-muted">Give the moderation team relevant context. This link accepts one submission.</p>
          <Textarea
            id="appeal-message"
            className="mt-4 min-h-40"
            value={message}
            maxLength={2000}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Explain what happened and include any context the moderators should consider."
          />
          <div className="mt-2 flex items-center justify-between text-xs text-muted">
            <span>Link expires {new Date(moderationCase.expiresAt).toLocaleString()}</span>
            <span>{message.length}/2000</span>
          </div>
          {error && <p className="mt-4 rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}
          <Button className="mt-5 w-full" loading={busy} disabled={message.trim().length < 10} onClick={submit}>
            Submit appeal
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
