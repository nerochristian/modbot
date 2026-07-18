'use client'

import { FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import Script from 'next/script'
import { ArrowRight, CheckCircle2, Loader2, RotateCcw, ShieldCheck, TriangleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'

type TurnstileRenderOptions = {
  sitekey: string
  action: string
  theme: 'dark'
  size: 'flexible'
  retry: 'auto'
  'retry-interval': number
  callback: (token: string) => void
  'expired-callback': () => void
  'timeout-callback': () => void
  'error-callback': (code?: string) => void
}

type TurnstileApi = {
  render: (target: HTMLElement, options: TurnstileRenderOptions) => string
  remove: (widgetId?: string) => void
  reset: (widgetId?: string) => void
}

declare global {
  interface Window {
    turnstile?: TurnstileApi
    __docketTurnstileReady?: () => void
  }
}

const TRANSIENT_ERROR_PREFIXES = ['300', '600']
const MAX_WIDGET_RETRIES = 3

function describeTurnstileError(code?: string): string {
  if (!code) return 'The human check could not load. Refresh the page and try again.'
  if (TRANSIENT_ERROR_PREFIXES.some((prefix) => code.startsWith(prefix))) {
    return `The human check lost its connection (error ${code}). Retrying automatically.`
  }
  if (code === '110200') {
    return `This verification address is not approved in Cloudflare yet (error ${code}). A server admin must add this hostname to the Turnstile widget.`
  }
  if (code.startsWith('110')) {
    return `The human check is misconfigured (error ${code}). Let a server admin know.`
  }
  return `The human check reported error ${code}. Refresh the page and try again.`
}

export function VerificationForm({ token, siteKey }: { token: string; siteKey: string }) {
  const [state, setState] = useState<'idle' | 'ready' | 'retrying' | 'submitting' | 'success' | 'error'>('idle')
  const [message, setMessage] = useState('')
  const [challenge, setChallenge] = useState('')
  const [canReset, setCanReset] = useState(true)
  const widgetHost = useRef<HTMLDivElement>(null)
  const widgetId = useRef<string | null>(null)
  const retries = useRef(0)
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const renderWidget = useCallback(() => {
    if (!widgetHost.current || !window.turnstile || widgetId.current) return
    widgetId.current = window.turnstile.render(widgetHost.current, {
      sitekey: siteKey,
      action: 'docket-verification',
      theme: 'dark',
      size: 'flexible',
      retry: 'auto',
      'retry-interval': 4_000,
      callback: (value) => {
        retries.current = 0
        setChallenge(value)
        setCanReset(true)
        setState('ready')
        setMessage('')
      },
      'expired-callback': () => {
        setChallenge('')
        setCanReset(true)
        setState('error')
        setMessage('The human check expired. Complete it again to continue.')
      },
      'timeout-callback': () => {
        setChallenge('')
        setState('retrying')
        setMessage('The human check timed out. Restarting it now.')
        if (window.turnstile && widgetId.current) window.turnstile.reset(widgetId.current)
      },
      'error-callback': (code) => {
        setChallenge('')
        const transient = !code || TRANSIENT_ERROR_PREFIXES.some((prefix) => code.startsWith(prefix))
        if (transient && retries.current < MAX_WIDGET_RETRIES) {
          retries.current += 1
          setCanReset(true)
          setState('retrying')
          setMessage(describeTurnstileError(code))
          retryTimer.current = setTimeout(() => {
            if (window.turnstile && widgetId.current) window.turnstile.reset(widgetId.current)
          }, 1_500)
          return
        }
        setCanReset(code !== '110200' && !code?.startsWith('110'))
        setState('error')
        setMessage(describeTurnstileError(code))
      },
    })
  }, [siteKey])

  useEffect(() => {
    window.__docketTurnstileReady = renderWidget
    if (window.turnstile) renderWidget()
    return () => {
      if (retryTimer.current) clearTimeout(retryTimer.current)
      if (widgetId.current && window.turnstile) window.turnstile.remove(widgetId.current)
      widgetId.current = null
      delete window.__docketTurnstileReady
    }
  }, [renderWidget])

  function resetChallenge() {
    retries.current = 0
    setChallenge('')
    setCanReset(true)
    setState('idle')
    setMessage('')
    if (widgetId.current && window.turnstile) window.turnstile.reset(widgetId.current)
  }

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
      setMessage('Your server access is open. You can return to Discord now.')
    } catch (error) {
      setState('error')
      setCanReset(true)
      setMessage(error instanceof Error ? error.message : 'Verification could not be completed')
      setChallenge('')
      if (widgetId.current && window.turnstile) window.turnstile.reset(widgetId.current)
    }
  }

  if (state === 'success') {
    return (
      <div className="relative overflow-hidden rounded-2xl border border-[#1c5a46] bg-[#0a241c] p-7 text-center">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[#43d99a] to-transparent" />
        <span className="mx-auto grid size-14 place-items-center rounded-2xl border border-[#287a5d] bg-[#0c3528] text-[#55e4a6] shadow-[0_0_32px_-12px_#43d99a]">
          <CheckCircle2 className="size-7" />
        </span>
        <p className="mt-5 font-mono text-[0.625rem] font-bold uppercase tracking-[0.2em] text-[#55e4a6]">Checkpoint passed</p>
        <h2 className="mt-2 font-display text-2xl font-semibold text-white">Access opened</h2>
        <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-[#a6c9ba]">{message}</p>
      </div>
    )
  }

  return (
    <>
      <Script
        src="https://challenges.cloudflare.com/turnstile/v0/api.js?onload=__docketTurnstileReady&render=explicit"
        strategy="afterInteractive"
        onReady={renderWidget}
      />
      <form onSubmit={submit} className="overflow-hidden rounded-2xl border border-[#1e3152] bg-[#0b1425]">
        <div className="flex items-center justify-between border-b border-[#1e3152] bg-[#0d192d] px-4 py-3 sm:px-5">
          <div className="flex items-center gap-2.5">
            <span className="grid size-8 place-items-center rounded-lg border border-[#2856a1] bg-[#0b234c] text-[#72a7ff]">
              <ShieldCheck className="size-4" />
            </span>
            <div>
              <p className="text-sm font-semibold text-white">Human check</p>
              <p className="mt-0.5 text-[0.6875rem] text-[#8291aa]">Private and single-use</p>
            </div>
          </div>
          <span className="font-mono text-[0.625rem] font-semibold uppercase tracking-[0.14em] text-[#6680a8]">Step 1 of 1</span>
        </div>

        <div className="space-y-4 p-3 sm:p-5">
          <div className="relative min-h-[72px] overflow-hidden rounded-xl border border-[#243652] bg-[#070d18] p-2">
            {(state === 'idle' || state === 'retrying') && !challenge && (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center gap-2 text-xs text-[#7f91ad]">
                <Loader2 className="size-4 animate-spin text-[#6ca2ff]" /> {state === 'retrying' ? 'Reconnecting secure check…' : 'Loading secure check…'}
              </div>
            )}
            <div ref={widgetHost} className="min-h-[56px]" aria-label="Cloudflare human verification" />
          </div>

          {state === 'error' && (
            <div className="flex items-start justify-between gap-3 rounded-xl border border-[#5a2832] bg-[#25131b] px-3.5 py-3 text-sm text-[#ff9baa]" role="alert">
              <span className="flex items-start gap-2 leading-5">
                <TriangleAlert className="mt-0.5 size-4 shrink-0" /> {message}
              </span>
              {canReset && (
                <button type="button" onClick={resetChallenge} className="focus-ring shrink-0 rounded-md p-1 text-[#ff9baa] transition hover:bg-[#3a1b25]" aria-label="Reset human check">
                  <RotateCcw className="size-4" />
                </button>
              )}
            </div>
          )}

          {state === 'retrying' && (
            <div className="flex items-start gap-2 rounded-xl border border-[#294066] bg-[#101d33] px-3.5 py-3 text-sm text-[#9db8e6]" role="status">
              <Loader2 className="mt-0.5 size-4 shrink-0 animate-spin" /> <span className="leading-5">{message}</span>
            </div>
          )}

          <Button
            type="submit"
            size="lg"
            className="h-12 w-full rounded-xl bg-gradient-to-r from-[#2563eb] to-[#1684ee] font-semibold shadow-[0_18px_40px_-18px_rgba(37,99,235,.95)]"
            disabled={state === 'submitting' || !challenge}
          >
            {state === 'submitting' ? <Loader2 className="size-4 animate-spin" /> : <ShieldCheck className="size-4" />}
            {state === 'submitting' ? 'Opening access…' : 'Verify and open access'}
            {state !== 'submitting' && <ArrowRight className="ml-auto size-4" />}
          </Button>
        </div>
      </form>
    </>
  )
}
