import Link from 'next/link'
import { Logo } from '@/components/logo'
import { PublicThemeToggle } from '@/components/marketing/theme-toggle'
import { ShieldCheck, Gavel, ShieldAlert } from 'lucide-react'

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-full lg:grid-cols-2">
      <div className="flex flex-col px-4 py-6 sm:px-8">
        <div className="flex items-center justify-between">
          <Link href="/" className="focus-ring rounded-lg">
            <Logo />
          </Link>
          <PublicThemeToggle />
        </div>
        <div className="flex flex-1 items-center justify-center py-10">
          <div className="w-full max-w-sm">{children}</div>
        </div>
        <p className="text-center text-xs text-muted-2">
          © 2026 Aegis · Demo environment
        </p>
      </div>

      {/* Decorative side panel */}
      <div
        className="relative hidden flex-col justify-between overflow-hidden p-12 lg:flex"
        style={{
          background:
            'linear-gradient(150deg, color-mix(in srgb, var(--accent) 88%, #000), color-mix(in srgb, var(--accent) 40%, #000))',
        }}
      >
        <div className="grid-texture pointer-events-none absolute inset-0 opacity-[0.12]" />
        <div
          className="pointer-events-none absolute inset-0 opacity-20"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 20%, white 0, transparent 40%), radial-gradient(circle at 80% 60%, white 0, transparent 35%)',
          }}
        />
        <Logo className="relative text-white [&_span]:text-white" />
        <div className="relative">
          <div className="flex gap-2 text-white/90">
            <ShieldAlert className="size-5" />
            <Gavel className="size-5" />
            <ShieldCheck className="size-5" />
          </div>
          <blockquote className="mt-5 max-w-md text-2xl font-medium leading-snug text-white">
            “Aegis turned our overwhelmed mod team into a calm one. Automod catches the noise, and
            every case and appeal lives in one place.”
          </blockquote>
          <p className="mt-5 text-sm text-white/80">Marcus Lee · Head Moderator, The Nexus</p>
        </div>
        <div className="relative flex gap-8 text-white/90">
          <div>
            <p className="text-2xl font-bold">2.5M+</p>
            <p className="text-sm text-white/70">Messages scanned daily</p>
          </div>
          <div>
            <p className="text-2xl font-bold">40k+</p>
            <p className="text-sm text-white/70">Communities protected</p>
          </div>
        </div>
      </div>
    </div>
  )
}
