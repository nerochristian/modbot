import type { Metadata } from 'next'
import { Clock, Lock, ShieldCheck, TriangleAlert } from 'lucide-react'
import { VerificationForm } from '@/components/verification/verification-form'
import { getBotGuildSettings } from '@/lib/bot-settings'
import { verifyVerificationCapability } from '@/lib/web-verification'

export const metadata: Metadata = { title: 'Server verification' }

export default async function VerifyPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params
  let error = ''
  let siteKey = ''
  try {
    const capability = verifyVerificationCapability(token)
    const settings = await getBotGuildSettings(capability.g)
    if (!settings.verification_enabled || settings.verification_method !== 'website') {
      throw new Error('Website verification is not active for this server')
    }
    siteKey = process.env.HCAPTCHA_SITE_KEY?.trim() || ''
    if (!siteKey) throw new Error('The server owner has not finished configuring the website check')
  } catch (reason) {
    error = reason instanceof Error ? reason.message : 'This verification link is invalid'
  }

  return (
    <main className="relative grid min-h-screen place-items-center overflow-hidden bg-paper px-4 py-10">
      <div className="pointer-events-none absolute inset-0 opacity-60 [background-image:radial-gradient(circle_at_15%_10%,var(--accent-soft),transparent_38%),radial-gradient(circle_at_85%_85%,var(--info-soft),transparent_34%)]" />
      <div className="pointer-events-none absolute inset-0 opacity-[0.035] [background-image:linear-gradient(var(--foreground)_1px,transparent_1px),linear-gradient(90deg,var(--foreground)_1px,transparent_1px)] [background-size:36px_36px]" />

      <section className="relative w-full max-w-md">
        <div className="overflow-hidden rounded-3xl border border-border-strong bg-card shadow-[0_40px_120px_-45px_rgba(0,0,0,.85)]">
          <header className="relative overflow-hidden border-b border-border bg-gradient-to-b from-surface-2 to-card px-7 pb-7 pt-8">
            <div className="pointer-events-none absolute -right-10 -top-10 size-40 rounded-full bg-accent-soft blur-3xl" />
            <div className="relative flex items-center justify-between">
              <p className="font-mono text-[0.625rem] font-bold uppercase tracking-[0.2em] text-accent">Docket identity gate</p>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-success/25 bg-success-soft px-2.5 py-1 text-[0.625rem] font-semibold text-success">
                <span className="size-1.5 rounded-full bg-success" /> Secure
              </span>
            </div>
            <div className="relative mt-5 flex items-center gap-4">
              <span className="grid size-14 shrink-0 place-items-center rounded-2xl border border-accent-line bg-accent-soft text-accent shadow-[inset_0_1px_0_rgba(255,255,255,.06)]">
                <ShieldCheck className="size-7" />
              </span>
              <div>
                <h1 className="font-display text-2xl font-semibold leading-tight text-foreground">Verify your access</h1>
                <p className="mt-1 text-sm text-muted">One quick check unlocks the server.</p>
              </div>
            </div>
          </header>

          <div className="px-7 py-7">
            {error ? (
              <div className="rounded-2xl border border-danger/30 bg-danger-soft p-6 text-center">
                <span className="mx-auto grid size-12 place-items-center rounded-full border border-danger/25 bg-danger/10 text-danger">
                  <TriangleAlert className="size-6" />
                </span>
                <h2 className="mt-4 font-display text-lg font-semibold text-foreground">This link cannot be used</h2>
                <p className="mt-2 text-sm leading-6 text-muted">{error}.</p>
                <p className="mt-3 text-xs leading-5 text-muted-2">Return to Discord and press Verify me again to get a fresh link.</p>
              </div>
            ) : (
              <VerificationForm token={token} siteKey={siteKey} />
            )}
          </div>
        </div>

        <div className="mt-4 flex items-center justify-center gap-5 text-[0.6875rem] font-medium text-muted-2">
          <span className="inline-flex items-center gap-1.5"><Lock className="size-3.5" /> No password</span>
          <span className="inline-flex items-center gap-1.5"><ShieldCheck className="size-3.5" /> No Discord login</span>
          <span className="inline-flex items-center gap-1.5"><Clock className="size-3.5" /> Single-use link</span>
        </div>
      </section>
    </main>
  )
}
