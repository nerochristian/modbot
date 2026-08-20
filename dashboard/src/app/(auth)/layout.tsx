import Link from 'next/link'
import { Logo } from '@/components/logo'
import { PublicThemeToggle } from '@/components/marketing/theme-toggle'

/**
 * Auth — the sign-in card floating over the same dark blue surface as the
 * landing page, so arriving here never feels like a different product.
 */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="situation relative flex min-h-full flex-col overflow-hidden bg-paper">
      <div className="soft-grid pointer-events-none absolute inset-0 opacity-60" />
      <div
        aria-hidden
        className="blue-orb pointer-events-none absolute left-1/2 top-[-16%] size-[42rem] -translate-x-1/2 rounded-full opacity-80"
      />

      <div className="relative z-10 flex items-center justify-between px-5 py-5 sm:px-8">
        <Link href="/" className="focus-ring rounded-md">
          <Logo />
        </Link>
        <PublicThemeToggle />
      </div>

      <div className="relative z-10 flex flex-1 items-center justify-center px-5 pb-10 pt-4">
        <div className="w-full max-w-[22rem]">{children}</div>
      </div>

      <div className="relative z-10 hidden items-center justify-between px-8 pb-5 font-mono text-[0.5625rem] uppercase tracking-[0.18em] text-muted-2 sm:flex">
        <span>the-nexus / #mod-log</span>
        <span>Discord-secured · no passwords stored</span>
      </div>
    </div>
  )
}
