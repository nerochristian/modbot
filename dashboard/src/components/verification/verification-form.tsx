'use client'

import { FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import Script from 'next/script'
import { ArrowRight, CheckCircle2, Loader2, ShieldCheck, TriangleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'

type RecaptchaApi = {
  ready: (cb: () => void) => void
  execute: (siteKey: string, options: { action: string }) => Promise<string>
}

declare global {
  interface Window {
    // reCAPTCHA Enterprise exposes grecaptcha.enterprise; the classic build
    // exposes grecaptcha directly. We support whichever the loaded script provides.
    grecaptcha?: RecaptchaApi & { enterprise?: RecaptchaApi }
  }
}

const RECAPTCHA_ACTION = 'verify'

export function VerificationForm({ token, siteKey }: { token: string; siteKey: string }) {
  const [state, setState] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle')
  const [message, setMessage] = useState('')
  const [scriptReady, setScriptReady] = useState(false)
  const readyRef = useRef(false)

  useEffect(() => {
    readyRef.current = scriptReady
  }, [scriptReady])

  // Run the invisible reCAPTCHA v3 flow and return a fresh token. v3 tokens
  // expire after ~2 minutes, so we execute at submit time rather than on load.
  const runChallenge = useCallback((): Promise<string> => {
    return new Promise((resolve, reject) => {
      const api = window.grecaptcha?.enterprise ?? window.grecaptcha
      if (!api) {
        reject(new Error('The human check could not load. Refresh the page and try again.'))
        return
      }
      api.ready(() => {
        api
          .execute(siteKey, { action: RECAPTCHA_ACTION })
          .then((tok) => {
            console.error('[verify-diag] execute token length:', tok ? tok.length : 'EMPTY')
            resolve(tok)
          })
          .catch((err) => {
            console.error('[verify-diag] execute failed:', err)
            reject(new Error('The human check could not be completed. Refresh the page and try again.'))
          })
      })
    })
  }, [siteKey])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (state === 'submitting') return
    setState('submitting')
    setMessage('')
    try {
      const challenge = await runChallenge()
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
      setMessage(error instanceof Error ? error.message : 'Verification could not be completed')
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
        src={`https://www.google.com/recaptcha/api.js?render=${encodeURIComponent(siteKey)}`}
        strategy="afterInteractive"
        onReady={() => setScriptReady(true)}
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
          <div className="flex items-start gap-3 rounded-xl border border-[#243652] bg-[#070d18] px-4 py-3.5">
            <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg border border-[#2856a1] bg-[#0b234c] text-[#72a7ff]">
              <ShieldCheck className="size-4" />
            </span>
            <div>
              <p className="text-sm font-medium text-[#dce6f5]">No puzzles, no clicking</p>
              <p className="mt-1 text-xs leading-5 text-[#8291aa]">
                We run a quick invisible check in the background. Just press the button below to confirm you&apos;re human.
              </p>
            </div>
          </div>

          {state === 'error' && (
            <div className="flex items-start gap-2 rounded-xl border border-[#5a2832] bg-[#25131b] px-3.5 py-3 text-sm text-[#ff9baa]" role="alert">
              <TriangleAlert className="mt-0.5 size-4 shrink-0" /> <span className="leading-5">{message}</span>
            </div>
          )}

          <Button
            type="submit"
            size="lg"
            className="h-12 w-full rounded-xl bg-gradient-to-r from-[#2563eb] to-[#1684ee] font-semibold shadow-[0_18px_40px_-18px_rgba(37,99,235,.95)]"
            disabled={state === 'submitting' || !scriptReady}
          >
            {state === 'submitting' ? <Loader2 className="size-4 animate-spin" /> : <ShieldCheck className="size-4" />}
            {state === 'submitting' ? 'Opening access…' : !scriptReady ? 'Loading secure check…' : 'Verify and open access'}
            {state !== 'submitting' && scriptReady && <ArrowRight className="ml-auto size-4" />}
          </Button>

          <p className="text-center text-[0.6875rem] leading-4 text-[#6680a8]">
            Protected by reCAPTCHA. Google&apos;s{' '}
            <a href="https://policies.google.com/privacy" target="_blank" rel="noreferrer" className="underline hover:text-[#8fb0e0]">Privacy Policy</a>{' '}
            and{' '}
            <a href="https://policies.google.com/terms" target="_blank" rel="noreferrer" className="underline hover:text-[#8fb0e0]">Terms</a>{' '}
            apply.
          </p>
        </div>
      </form>
    </>
  )
}
