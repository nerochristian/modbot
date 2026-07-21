import Link from 'next/link'
import { Logo } from '@/components/logo'

const LINKS = [
  { label: 'Features', href: '/#features' },
  { label: 'How it works', href: '/#setup' },
  { label: 'Commands', href: '/commands' },
  { label: 'Support', href: '/commands#support' },
  { label: 'Dashboard', href: '/dashboard' },
]

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-surface">
      <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
        <div className="flex flex-col justify-between gap-8 md:flex-row md:items-start">
          <div className="space-y-4">
            <Logo />
            <p className="max-w-md text-sm leading-6 text-muted">
              Automod, cases, member reports, tickets, appeals, and staff actions for your Discord server.
            </p>
          </div>
          <nav className="flex max-w-lg flex-wrap gap-x-6 gap-y-3" aria-label="Footer navigation">
            {LINKS.map((link) => (
              <Link key={link.label} href={link.href} className="text-sm text-muted transition-colors hover:text-foreground">
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="mt-10 flex flex-col justify-between gap-3 border-t border-border pt-6 font-mono text-xs text-muted-2 sm:flex-row">
          <p>© 2026 Docket.</p>
          <p>Dashboard access follows your live Discord Administrator permission.</p>
        </div>
      </div>
    </footer>
  )
}
