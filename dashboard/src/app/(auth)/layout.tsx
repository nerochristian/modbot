import Link from 'next/link'
import { Logo } from '@/components/logo'
import { PublicThemeToggle } from '@/components/marketing/theme-toggle'
import { CircuitField } from '@/components/marketing/circuit-field'

/**
 * Auth — the desk threshold. Not a two-pane storefront; a single lock card
 * suspended over the room you'll be let into. Quiet, weighted, deliberate.
 */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="situation relative flex min-h-full flex-col overflow-hidden bg-paper">
      <CircuitField className="pointer-events-none absolute inset-0 h-full w-full opacity-30" />
      <div className="field-grid-fade grid-texture pointer-events-none absolute inset-0 opacity-40" />
      <div
        className="pointer-events-none absolute left-1/2 top-[-20%] size-[42rem] -translate-x-1/2 rounded-full opacity-[0.12] blur-[130px] field-drift"
        style={{ background: 'radial-gradient(circle, var(--brand-from), transparent 70%)' }}
      />

      {/* top chrome */}
      <div className="relative z-10 flex items-center justify-between px-5 py-5 sm:px-8">
        <Link href="/" className="focus-ring rounded-md">
          <Logo />
        </Link>
        <PublicThemeToggle />
      </div>

      {/* the threshold */}
      <div className="relative z-10 flex flex-1 items-center justify-center px-5 pb-10 pt-4">
        <div className="w-full max-w-[21.5rem]">
          {children}
        </div>
      </div>

      {/* bottom margin — the room, breathing under the lock */}
      <div className="relative z-10 hidden items-center justify-between px-8 pb-5 font-mono text-[0.5625rem] uppercase tracking-[0.18em] text-muted-2 sm:flex">
        <span>the-nexus / field</span>
        <span>Discord-secured · no passwords on this desk</span>
      </div>
    </div>
  )
}
