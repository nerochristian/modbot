'use client'

import { useState } from 'react'
import { CheckCircle2, FileWarning } from 'lucide-react'
import { Badge, statusTone } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Field, Input, Textarea } from '@/components/ui/input'
import type { TicketQuestion } from '@/lib/modules-contract'

type AppealCase = { ref: number; action: string; reason: string; status: string; createdAt: string; expiresAt: string }

export function AppealForm({ token, moderationCase, questions }: { token: string; moderationCase: AppealCase; questions: TicketQuestion[] }) {
  const [answers, setAnswers] = useState<Record<string, string>>(() => Object.fromEntries(questions.map((question) => [question.id, ''])))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [receipt, setReceipt] = useState<number | null>(null)
  const complete = questions.every((question) => !question.required || (answers[question.id] ?? '').trim().length >= 3)

  async function submit() {
    setBusy(true)
    setError('')
    try {
      const response = await fetch(`/api/appeals/public/${encodeURIComponent(token)}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ answers }) })
      const body = await response.json().catch(() => ({}))
      if (!response.ok) { setError(body.issues?.[0]?.message ?? body.error ?? 'The appeal could not be submitted.'); return }
      setReceipt(Number(body.ref))
    } catch {
      setError('The appeal service could not be reached. Check your connection and try again.')
    } finally { setBusy(false) }
  }

  if (receipt !== null) return (
    <Card className="border-success/30"><CardContent className="py-10 text-center"><CheckCircle2 className="mx-auto size-9 text-success" /><h1 className="mt-4 font-display text-2xl font-semibold text-foreground">Appeal submitted</h1><p className="mt-2 text-sm text-muted">Your appeal reference is <span className="font-mono font-semibold text-foreground">APL-{String(receipt).padStart(4, '0')}</span>. The server moderation team can now review it.</p></CardContent></Card>
  )

  return (
    <div className="space-y-4">
      <Card><CardContent className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-3"><span className="grid size-10 place-items-center rounded-lg bg-danger-soft text-danger"><FileWarning className="size-5" /></span><div><p className="font-mono text-xs uppercase tracking-[0.12em] text-muted">Punishment record</p><h1 className="font-display text-xl font-semibold text-foreground">CASE-{String(moderationCase.ref).padStart(4, '0')}</h1></div></div><div className="flex gap-2"><Badge tone={statusTone(moderationCase.action)}>{moderationCase.action}</Badge><Badge tone={statusTone(moderationCase.status)}>{moderationCase.status}</Badge></div></div>
        <div className="grid grid-cols-[1.25rem_1fr] gap-x-3"><div className="flex flex-col items-center"><span className="mt-1 size-2 rounded-full bg-danger" /><span className="my-1 w-px flex-1 bg-border" /><span className="mb-1 size-2 rounded-full bg-accent" /></div><div className="space-y-4"><div><p className="text-xs font-medium uppercase tracking-wide text-muted">Recorded reason</p><p className="mt-1 whitespace-pre-wrap text-sm leading-6 text-foreground">{moderationCase.reason}</p></div><div><p className="text-xs font-medium uppercase tracking-wide text-muted">Your next step</p><p className="mt-1 text-sm leading-6 text-foreground">Submit one statement for the server staff team to review.</p></div></div></div>
      </CardContent></Card>
      <Card><CardContent>
        <div><p className="font-display text-lg font-semibold text-foreground">Appeal statement</p><p className="mt-1 text-sm text-muted">Answer the server&apos;s questions carefully. This private link accepts one submission.</p></div>
        <div className="mt-5 space-y-5">{questions.map((question) => { const value = answers[question.id] ?? ''; const max = question.style === 'short' ? 300 : 2000; return <div key={question.id}><Field label={`${question.label}${question.required ? ' *' : ''}`}>{question.style === 'short' ? <Input value={value} maxLength={max} placeholder={question.placeholder} onChange={(event) => setAnswers((current) => ({ ...current, [question.id]: event.target.value }))} /> : <Textarea className="min-h-32" value={value} maxLength={max} placeholder={question.placeholder} onChange={(event) => setAnswers((current) => ({ ...current, [question.id]: event.target.value }))} />}</Field><p className="mt-1 text-right text-xs text-muted">{value.length}/{max}</p></div> })}</div>
        <div className="mt-2 flex items-center justify-between text-xs text-muted"><span>Link expires {new Date(moderationCase.expiresAt).toLocaleString()}</span><span>Required fields are marked *</span></div>
        {error && <p className="mt-4 rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}
        <Button className="mt-5 w-full" loading={busy} disabled={!complete} onClick={submit}>Submit appeal for staff review</Button>
      </CardContent></Card>
    </div>
  )
}
