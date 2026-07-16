'use client'

import { FormEvent, useState } from 'react'
import Script from 'next/script'
import { CheckCircle2, Loader2, ShieldCheck, TriangleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function VerificationForm({ token, siteKey }: { token: string; siteKey: string }) {
  const [state, setState] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle')
  const [message, setMessage] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const challenge = String(form.get('cf-turnstile-response') ?? '')
    if (!challenge) {
      setState('error')
      setMessage('Complete the human check before continuing.')
      return
    }
    setState('submitting')
    setMessage('')
    try {
      const response = await fetch(`/api/verify/${encodeURIComponent(token)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ challenge }),
      })
      const body = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(body.error || 'Verification could not be completed')
      setState('success')
      setMessage('You are verified. Return to Discord—your server access is ready.')
    } catch (error) {
      setState('error')
      setMessage(error instanceof Error ? error.message : 'Verification could not be completed')
    }
  }

  if (state === 'success') {
    return (
      <div className="rounded-xl border border-success/35 bg-success-soft p-6 text-center">
        <CheckCircle2 className="mx-auto size-10 text-success" />
        <h2 className="mt-3 font-display text-xl font-semibold text-foreground">Access granted</h2>
        <p className="mt-2 text-sm leading-6 text-muted">{message}</p>
      </div>
    )
  }

  return (
    <>
      <Script src="https://challenges.cloudflare.com/turnstile/v0/api.js" strategy="afterInteractive" />
      <form onSubmit={submit} className="space-y-5">
        <div className="flex items-start gap-3 rounded-xl border border-border bg-surface-2 p-4">
          <ShieldCheck className="mt-0.5 size-5 shrink-0 text-accent" />
          <div>
            <p className="text-sm font-semibold text-foreground">Private human check</p>
            <p className="mt-1 text-xs leading-5 text-muted">Docket uses Cloudflare Turnstile. Your challenge result is single-use and expires with this link.</p>
          </div>
        </div>
        <div className="min-h-[70px] overflow-hidden rounded-lg">
          <div className="cf-turnstile" data-sitekey={siteKey} data-action="docket-verification" data-theme="auto" data-size="flexible" />
        </div>
        {state === 'error' && (
          <div className="flex items-start gap-2 text-sm text-danger" role="alert">
            <TriangleAlert className="mt-0.5 size-4 shrink-0" /> {message}
          </div>
        )}
        <Button type="submit" className="w-full" disabled={state === 'submitting'}>
          {state === 'submitting' ? <Loader2 className="size-4 animate-spin" /> : <ShieldCheck className="size-4" />}
          {state === 'submitting' ? 'Verifying…' : 'Verify and unlock Discord'}
        </Button>
      </form>
    </>
  )
}
