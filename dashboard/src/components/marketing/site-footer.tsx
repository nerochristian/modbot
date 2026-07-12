import Link from 'next/link'
import { Logo } from '@/components/logo'

const GROUPS = [
  {
    title: 'Product',
    links: [
      { label: 'Automod', href: '#features' },
      { label: 'Cases', href: '#features' },
      { label: 'Appeals', href: '#features' },
      { label: 'Pricing', href: '#pricing' },
    ],
  },
  {
    title: 'Company',
    links: [
      { label: 'About', href: '#' },
      { label: 'Careers', href: '#' },
      { label: 'Blog', href: '#' },
      { label: 'Contact', href: '#' },
    ],
  },
  {
    title: 'Resources',
    links: [
      { label: 'Documentation', href: '#' },
      { label: 'Setup guide', href: '#' },
      { label: 'Status', href: '#' },
      { label: 'Support', href: '#' },
    ],
  },
  {
    title: 'Legal',
    links: [
      { label: 'Privacy', href: '#' },
      { label: 'Terms', href: '#' },
      { label: 'Security', href: '#' },
      { label: 'DPA', href: '#' },
    ],
  },
]

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-surface">
      <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <div className="grid gap-10 lg:grid-cols-[1.4fr_repeat(4,1fr)]">
          <div className="space-y-4">
            <Logo />
            <p className="max-w-xs text-sm text-muted">
              The moderation records desk for serious Discord communities. Stop raids and spam
              automatically, file every action as a case, and give your whole team one console.
            </p>
          </div>
          {GROUPS.map((group) => (
            <div key={group.title}>
              <h3 className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.16em] text-muted-2">{group.title}</h3>
              <ul className="mt-3 space-y-2.5">
                {group.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm text-muted transition-colors hover:text-foreground"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-border pt-6 sm:flex-row">
          <p className="font-mono text-xs text-muted-2">© 2026 Docket, Inc. All rights reserved.</p>
          <p className="font-mono text-xs text-muted-2">Built for demonstration — no real data.</p>
        </div>
      </div>
    </footer>
  )
}
