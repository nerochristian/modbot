import type { Metadata } from 'next'
import Image from 'next/image'
import { Check, LockKeyhole, ShieldCheck, TriangleAlert } from 'lucide-react'
import { VerificationForm } from '@/components/verification/verification-form'
import { getBotGuildSettings } from '@/lib/bot-settings'
import { verifyVerificationCapability } from '@/lib/web-verification'

export const metadata: Metadata = { title: 'Secure member verification' }

const assurances = [
  'No password or Discord login',
  'Single-use verification link',
  'Access updates automatically',
]

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
    <main className="relative min-h-[100svh] overflow-hidden bg-[#050814] px-4 py-5 text-[#f5f8ff] sm:grid sm:place-items-center sm:px-6 sm:py-10">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_14%_8%,rgba(47,123,255,.20),transparent_30rem),radial-gradient(circle_at_92%_88%,rgba(35,211,238,.09),transparent_26rem)]" />
      <div className="pointer-events-none absolute inset-0 opacity-35 [background-image:linear-gradient(rgba(118,143,184,.08)_1px,transparent_1px),linear-gradient(90deg,rgba(118,143,184,.08)_1px,transparent_1px)] [background-size:52px_52px] [mask-image:linear-gradient(to_bottom,black,transparent_86%)]" />

      <section className="relative mx-auto w-full max-w-[620px] overflow-hidden rounded-[1.75rem] border border-[#1d2b45] bg-[#0a1020]/95 shadow-[0_32px_100px_-34px_rgba(0,63,190,.7)] backdrop-blur-xl">
        <div className="h-1 bg-gradient-to-r from-[#1f64ff] via-[#38bdf8] to-[#1f64ff]" />

        <header className="flex items-center justify-between border-b border-[#1d2b45] px-5 py-4 sm:px-7">
          <div className="flex items-center gap-3">
            <span className="grid size-11 place-items-center overflow-hidden rounded-xl border border-[#2d5ca5] bg-[#071228] shadow-[0_0_24px_-8px_rgba(47,123,255,.9)]">
              <Image src="/brand/docket-glyph.png" alt="Docket" width={44} height={44} priority className="size-10 object-contain" />
            </span>
            <div>
              <p className="font-display text-lg font-semibold leading-none">Docket</p>
              <p className="mt-1 font-mono text-[0.625rem] font-semibold uppercase tracking-[0.16em] text-[#7f91ad]">Member access control</p>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-[#1f4739] bg-[#09241c] px-3 py-1.5 font-mono text-[0.625rem] font-semibold uppercase tracking-[0.12em] text-[#56d99b]">
            <span className="size-1.5 rounded-full bg-[#34d98b] shadow-[0_0_10px_#34d98b]" />
            Protected
          </div>
        </header>

        <div className="px-5 py-7 sm:px-8 sm:py-9">
          <div className="mb-7 border-l-2 border-[#2f7bff] pl-4 sm:pl-5">
            <p className="font-mono text-[0.625rem] font-bold uppercase tracking-[0.2em] text-[#6ca2ff]">Access checkpoint</p>
            <h1 className="mt-3 max-w-lg font-display text-[2rem] font-semibold leading-[1.05] tracking-[-0.035em] sm:text-[2.65rem]">
              Prove you&apos;re human.<br />Keep the bots out.
            </h1>
            <p className="mt-4 max-w-lg text-sm leading-6 text-[#9cabc2] sm:text-[0.95rem]">
              Complete one private Cloudflare check. Docket will update your server access the moment you pass.
            </p>
          </div>

          <div className="mb-7 grid gap-2.5 sm:grid-cols-3">
            {assurances.map((assurance) => (
              <div key={assurance} className="flex items-center gap-2 rounded-xl border border-[#1b2941] bg-[#0d1628] px-3 py-2.5 text-xs text-[#b7c2d5] sm:items-start">
                <Check className="mt-px size-3.5 shrink-0 text-[#54d9a0]" />
                <span className="leading-4">{assurance}</span>
              </div>
            ))}
          </div>

          {error ? (
            <div className="rounded-2xl border border-[#5a2832] bg-[#25131b] p-6 text-center">
              <span className="mx-auto grid size-12 place-items-center rounded-2xl border border-[#74323e] bg-[#351721] text-[#ff7185]">
                <TriangleAlert className="size-5" />
              </span>
              <h2 className="mt-4 font-display text-xl font-semibold">This checkpoint is closed</h2>
              <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-[#c7a8af]">
                {error}. Return to Discord and press <strong className="text-white">Start verification</strong> for a new link.
              </p>
            </div>
          ) : (
            <VerificationForm token={token} siteKey={siteKey} />
          )}
        </div>

        <footer className="flex flex-col gap-2 border-t border-[#1d2b45] bg-[#080e1b] px-5 py-4 text-[0.6875rem] text-[#71809a] sm:flex-row sm:items-center sm:justify-between sm:px-7">
          <span className="flex items-center gap-1.5"><ShieldCheck className="size-3.5 text-[#6ca2ff]" /> Secured by Docket + Cloudflare Turnstile</span>
          <span className="flex items-center gap-1.5 font-mono uppercase tracking-[0.1em]"><LockKeyhole className="size-3" /> Private session</span>
        </footer>
      </section>
    </main>
  )
}
