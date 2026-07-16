import type { Metadata } from 'next'
import { ShieldCheck, TriangleAlert } from 'lucide-react'
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
    siteKey = process.env.TURNSTILE_SITE_KEY?.trim() || ''
    if (!siteKey) throw new Error('The server owner has not finished configuring the website check')
  } catch (reason) {
    error = reason instanceof Error ? reason.message : 'This verification link is invalid'
  }

  return (
    <main className="relative grid min-h-screen place-items-center overflow-hidden bg-paper px-4 py-12">
      <div className="pointer-events-none absolute inset-0 opacity-50 [background-image:radial-gradient(circle_at_20%_20%,var(--accent-soft),transparent_34%),radial-gradient(circle_at_80%_75%,var(--info-soft),transparent_30%)]" />
      <section className="relative w-full max-w-lg overflow-hidden rounded-2xl border border-border-strong bg-card shadow-[0_32px_100px_-40px_rgba(0,0,0,.75)]">
        <header className="border-b border-border bg-surface-2 p-6 sm:p-8">
          <p className="font-mono text-[0.625rem] font-bold uppercase tracking-[0.18em] text-accent">Docket identity gate</p>
          <div className="mt-4 flex items-center gap-3">
            <span className="grid size-11 place-items-center rounded-xl border border-accent-line bg-accent-soft text-accent"><ShieldCheck className="size-5" /></span>
            <div>
              <h1 className="font-display text-2xl font-semibold text-foreground">Verify your access</h1>
              <p className="mt-1 text-sm text-muted">One protected check. No password. No Discord login.</p>
            </div>
          </div>
        </header>
        <div className="p-6 sm:p-8">
          {error ? (
            <div className="rounded-xl border border-danger/30 bg-danger-soft p-5 text-center">
              <TriangleAlert className="mx-auto size-8 text-danger" />
              <h2 className="mt-3 font-semibold text-foreground">This link cannot be used</h2>
              <p className="mt-2 text-sm leading-6 text-muted">{error}. Return to Discord and press Start Verification again.</p>
            </div>
          ) : (
            <VerificationForm token={token} siteKey={siteKey} />
          )}
        </div>
      </section>
    </main>
  )
}
