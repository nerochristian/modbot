'use client'

import { FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import Script from 'next/script'
import { CheckCircle2, Loader2, ShieldCheck, TriangleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'

type TurnstileRenderOptions = {
  sitekey: string
  action?: string
  theme?: 'auto' | 'light' | 'dark'
  size?: 'normal' | 'flexible' | 'compact'
  retry?: 'auto' | 'never'
  'retry-interval'?: number
  callback?: (token: string) => void
  'error-callback'?: (code?: string) => void
  'timeout-callback'?: () => void
  'expired-callback'?: () => void
}

type Turnstile = {
  render: (container: HTMLElement, options: TurnstileRenderOptions) => string
  reset: (widgetId?: string) => void
  remove: (widgetId?: string) => void
}

declare global {
  interface Window {
    turnstile?: Turnstile
    __docketTurnstileReady?: () => void
  }
}

// Cloudflare's "Unable to connect" surfaces as a 1100xx network error. These
// are transient far more often than they are terminal, so we reset the widget
// a few times before giving up and telling the visitor what actually failed.
const NETWORK_ERROR_PREFIXES = ['1100', '1101', '1102', '600']
const MAX_WIDGET_RETRIES = 3

function describeTurnstileError(code?: string): string {
  if (!code) return 'The human check could not load. Refresh the page and try again.'
  if (NETWORK_ERROR_PREFIXES.some((prefix) => code.startsWith(prefix))) {
    return `Could not reach the human check (error ${code}). This is usually a temporary network issue—retrying automatically.`
  }
  if (code.startsWith('1100')) return `The human check failed to initialize (error ${code}).`
  return `The human check reported error ${code}. Refresh the page and try again.`
}

export function VerificationForm({ token, siteKey }: { token: string; siteKey: string }) {
  const [state, setState] = useState<'idle' | 'ready' | 'submitting' | 'success' | 'error'>('idle')
  const [message, setMessage] = useState('')
  const [challenge, setChallenge] = useState('')
  const containerRef = useRef<HTMLDivElement | null>(null)
  const widgetIdRef = useRef<string | null>(null)
  const retriesRef = useRef(0)

  const renderWidget = useCallback(() => {
    if (!window.turnstile || !containerRef.current) return
    if (widgetIdRef.current !== null) {
      window.turnstile.reset(widgetIdRef.current)
      return
    }
    widgetIdRef.current = window.turnstile.render(containerRef.current, {
      sitekey: siteKey,
      action: 'docket-verification',
      theme: 'auto',
      size: 'flexible',
      retry: 'auto',
      'retry-interval': 4_000,
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
      'timeout-callback': () => {
        if (window.turnstile && widgetIdRef.current !== null) window.turnstile.reset(widgetIdRef.current)
      },
      'error-callback': (code) => {
        setChallenge('')
        const transient = !code || NETWORK_ERROR_PREFIXES.some((prefix) => code.startsWith(prefix))
        if (transient && retriesRef.current < MAX_WIDGET_RETRIES) {
          retriesRef.current += 1
          setMessage(describeTurnstileError(code))
          setTimeout(() => {
            if (window.turnstile && widgetIdRef.current !== null) window.turnstile.reset(widgetIdRef.current)
          }, 1_500)
          return
        }
        setState('error')
        setMessage(describeTurnstileError(code))
      },
    })
  }, [siteKey])

  useEffect(() => {
    window.__docketTurnstileReady = renderWidget
    if (window.turnstile) renderWidget()
    return () => {
      if (window.turnstile && widgetIdRef.current !== null) {
        try {
          window.turnstile.remove(widgetIdRef.current)
        } catch {
          // widget already gone
        }
      }
      widgetIdRef.current = null
      delete window.__docketTurnstileReady
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
      if (window.turnstile && widgetIdRef.current !== null) window.turnstile.reset(widgetIdRef.current)
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
      <Script
        src="https://challenges.cloudflare.com/turnstile/v0/api.js?onload=__docketTurnstileReady&render=explicit"
        strategy="afterInteractive"
      />
      <form onSubmit={submit} className="space-y-5">
        <div className="flex items-start gap-3 rounded-xl border border-border bg-surface-2 p-4">
          <ShieldCheck className="mt-0.5 size-5 shrink-0 text-accent" />
          <div>
            <p className="text-sm font-semibold text-foreground">Private human check</p>
            <p className="mt-1 text-xs leading-5 text-muted">Docket uses Cloudflare Turnstile. Your challenge result is single-use and expires with this link.</p>
          </div>
        </div>
        <div ref={containerRef} className="min-h-[70px] overflow-hidden rounded-lg" />
        {state === 'error' && (
          <div className="flex items-start gap-2 text-sm text-danger" role="alert">
            <TriangleAlert className="mt-0.5 size-4 shrink-0" /> {message}
          </div>
        )}
        <Button type="submit" className="w-full" disabled={state === 'submitting' || !challenge}>
          {state === 'submitting' ? <Loader2 className="size-4 animate-spin" /> : <ShieldCheck className="size-4" />}
          {state === 'submitting' ? 'Verifying…' : 'Verify and unlock Discord'}
        </Button>
      </form>
    </>
  )
}
