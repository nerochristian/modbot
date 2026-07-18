'use client'

import { FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import Script from 'next/script'
import { CheckCircle2, Loader2, ShieldCheck, TriangleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'

type HCaptchaRenderOptions = {
  sitekey: string
  theme?: 'light' | 'dark'
  size?: 'normal' | 'compact' | 'invisible'
  callback?: (token: string) => void
  'error-callback'?: (code?: string) => void
  'chalexpired-callback'?: () => void
  'expired-callback'?: () => void
}

type HCaptcha = {
  render: (container: HTMLElement, options: HCaptchaRenderOptions) => string
  reset: (widgetId?: string) => void
  remove: (widgetId?: string) => void
}

declare global {
  interface Window {
    hcaptcha?: HCaptcha
    __docketHcaptchaReady?: () => void
  }
}

// hCaptcha error names that are genuinely transient (connectivity/challenge
// execution). These are worth resetting the widget for. Config problems
// (invalid sitekey, etc.) are deliberately NOT here: retrying them just loops
// forever on something only the server owner can fix.
const TRANSIENT_ERRORS = new Set(['network-error', 'challenge-error', 'rate-limited'])
const MAX_WIDGET_RETRIES = 3

function describeHcaptchaError(code?: string): string {
  if (!code) return 'The human check could not load. Refresh the page and try again.'
  if (TRANSIENT_ERRORS.has(code)) {
    return `Could not reach the human check (${code}). This is usually a temporary network issue—retrying automatically.`
  }
  if (code === 'invalid-sitekey' || code === 'invalid-data') {
    return `The human check is misconfigured (${code}). Please let a server admin know.`
  }
  return `The human check reported an error (${code}). Refresh the page and try again.`
}

export function VerificationForm({ token, siteKey }: { token: string; siteKey: string }) {
  const [state, setState] = useState<'idle' | 'ready' | 'submitting' | 'success' | 'error' | 'retrying'>('idle')
  const [message, setMessage] = useState('')
  const [challenge, setChallenge] = useState('')
  const containerRef = useRef<HTMLDivElement | null>(null)
  const widgetIdRef = useRef<string | null>(null)
  const retriesRef = useRef(0)

  const renderWidget = useCallback(() => {
    if (!window.hcaptcha || !containerRef.current) return
    if (widgetIdRef.current !== null) {
      window.hcaptcha.reset(widgetIdRef.current)
      return
    }
    widgetIdRef.current = window.hcaptcha.render(containerRef.current, {
      sitekey: siteKey,
      theme: 'dark',
      size: 'normal',
      callback: (value) => {
        retriesRef.current = 0
        setChallenge(value)
        setState((prev) => (prev === 'submitting' || prev === 'success' ? prev : 'ready'))
        setMessage('')
      },
      'expired-callback': () => {
        setChallenge('')
        setState('idle')
      },
      'chalexpired-callback': () => {
        setChallenge('')
        setState('idle')
        if (window.hcaptcha && widgetIdRef.current !== null) window.hcaptcha.reset(widgetIdRef.current)
      },
      'error-callback': (code) => {
        setChallenge('')
        const transient = !code || TRANSIENT_ERRORS.has(code)
        if (transient && retriesRef.current < MAX_WIDGET_RETRIES) {
          retriesRef.current += 1
          setState('retrying')
          setMessage(describeHcaptchaError(code))
          setTimeout(() => {
            if (window.hcaptcha && widgetIdRef.current !== null) window.hcaptcha.reset(widgetIdRef.current)
          }, 1_500)
          return
        }
        setState('error')
        setMessage(describeHcaptchaError(code))
      },
    })
  }, [siteKey])

  useEffect(() => {
    window.__docketHcaptchaReady = renderWidget
    if (window.hcaptcha) renderWidget()
    return () => {
      if (window.hcaptcha && widgetIdRef.current !== null) {
        try {
          window.hcaptcha.remove(widgetIdRef.current)
        } catch {
          // widget already gone
        }
      }
      widgetIdRef.current = null
      delete window.__docketHcaptchaReady
    }
  }, [renderWidget])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
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
      setChallenge('')
      if (window.hcaptcha && widgetIdRef.current !== null) window.hcaptcha.reset(widgetIdRef.current)
    }
  }

  if (state === 'success') {
    return (
      <div className="rounded-2xl border border-success/35 bg-success-soft p-7 text-center">
        <span className="mx-auto grid size-14 place-items-center rounded-full border border-success/30 bg-success/10 text-success">
          <CheckCircle2 className="size-8" />
        </span>
        <h2 className="mt-4 font-display text-xl font-semibold text-foreground">Access granted</h2>
        <p className="mt-2 text-sm leading-6 text-muted">{message}</p>
        <p className="mt-4 inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-2/60 px-3 py-1 text-xs font-medium text-muted-2">
          You can close this tab
        </p>
      </div>
    )
  }

  return (
    <>
      <Script
        src="https://js.hcaptcha.com/1/api.js?onload=__docketHcaptchaReady&render=explicit"
        strategy="afterInteractive"
      />
      <form onSubmit={submit} className="space-y-4">
        <div className="flex items-start gap-3 rounded-2xl border border-border bg-surface-2/60 p-4">
          <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg border border-accent-line bg-accent-soft text-accent">
            <ShieldCheck className="size-4" />
          </span>
          <div>
            <p className="text-sm font-semibold text-foreground">Private human check</p>
            <p className="mt-1 text-xs leading-5 text-muted">Powered by hCaptcha. Your result is single-use and expires with this link.</p>
          </div>
        </div>

        <div className="relative min-h-[72px] overflow-hidden rounded-2xl border border-border bg-surface-2/40 p-2">
          {(state === 'idle' || state === 'retrying') && !challenge && (
            <div className="pointer-events-none absolute inset-2 grid place-items-center rounded-xl bg-surface-2/60">
              <span className="inline-flex items-center gap-2 text-xs font-medium text-muted-2">
                <Loader2 className="size-3.5 animate-spin" /> Loading secure check…
              </span>
            </div>
          )}
          <div ref={containerRef} className="relative grid min-h-[64px] place-items-center [&_iframe]:!rounded-lg" />
        </div>

        {state === 'error' && (
          <div className="flex items-start gap-2 rounded-xl border border-danger/25 bg-danger-soft px-3 py-2.5 text-sm text-danger" role="alert">
            <TriangleAlert className="mt-0.5 size-4 shrink-0" /> <span className="leading-5">{message}</span>
          </div>
        )}
        {state === 'retrying' && (
          <div className="flex items-start gap-2 rounded-xl border border-border bg-surface-2/60 px-3 py-2.5 text-sm text-muted" role="status">
            <Loader2 className="mt-0.5 size-4 shrink-0 animate-spin" /> <span className="leading-5">{message}</span>
          </div>
        )}

        <Button type="submit" size="lg" className="w-full" disabled={state === 'submitting' || !challenge}>
          {state === 'submitting' ? <Loader2 className="size-4 animate-spin" /> : <ShieldCheck className="size-4" />}
          {state === 'submitting' ? 'Verifying…' : 'Verify and unlock Discord'}
        </Button>
        {!challenge && state !== 'submitting' && (
          <p className="text-center text-xs text-muted-2">Complete the check above to enable this button.</p>
        )}
      </form>
    </>
  )
}
