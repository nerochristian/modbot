import Link from 'next/link'
import { Logo } from '@/components/logo'

const LINKS = [
  { label: 'Commands', href: '/commands' },
  { label: 'How it works', href: '/#pipeline' },
  { label: 'Support', href: '/commands#support' },
  { label: 'Dashboard', href: '/dashboard' },
]

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-surface/45 backdrop-blur-xl">
      <div className="mx-auto max-w-7xl px-5 py-12 sm:px-8">
        <div className="flex flex-col justify-between gap-8 md:flex-row md:items-start">
          <div className="space-y-4">
            <Logo />
            <p className="max-w-md text-sm leading-6 text-muted">
              One modern control center for Discord moderation, member reports, tickets, cases, and server safety.
            </p>
          </div>
          <nav className="flex flex-wrap gap-x-6 gap-y-3">
            {LINKS.map((link) => (
              <Link key={link.label} href={link.href} className="text-sm font-medium text-muted transition-colors hover:text-foreground">
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="mt-10 flex flex-col justify-between gap-3 border-t border-border pt-6 text-xs text-muted-2 sm:flex-row">
          <p>© 2026 Docket. Built for Discord moderation teams.</p>
          <p>Access follows your live Discord Administrator permissions.</p>
        </div>
      </div>
    </footer>
  )
}
