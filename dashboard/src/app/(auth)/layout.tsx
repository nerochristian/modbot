import Link from 'next/link'
import { Logo } from '@/components/logo'
import { PublicThemeToggle } from '@/components/marketing/theme-toggle'
import { Star } from 'lucide-react'

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
          © 2026 Nebula, Inc. · Demo environment
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
        <div
          className="pointer-events-none absolute inset-0 opacity-20"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 20%, white 0, transparent 40%), radial-gradient(circle at 80% 60%, white 0, transparent 35%)',
          }}
        />
        <Logo className="relative text-white [&_span]:text-white" />
        <div className="relative">
          <div className="flex gap-0.5 text-white">
            {Array.from({ length: 5 }).map((_, i) => (
              <Star key={i} className="size-5 fill-current" />
            ))}
          </div>
          <blockquote className="mt-5 max-w-md text-2xl font-medium leading-snug text-white">
            “Nebula gave every team in our company the exact dashboard they needed — and cut our
            reporting time by 80%.”
          </blockquote>
          <p className="mt-5 text-sm text-white/80">Sarah Chen · VP Growth, Loop</p>
        </div>
        <div className="relative flex gap-8 text-white/90">
          <div>
            <p className="text-2xl font-bold">4,200+</p>
            <p className="text-sm text-white/70">Teams onboard</p>
          </div>
          <div>
            <p className="text-2xl font-bold">99.99%</p>
            <p className="text-sm text-white/70">Uptime SLA</p>
          </div>
        </div>
      </div>
    </div>
  )
}
