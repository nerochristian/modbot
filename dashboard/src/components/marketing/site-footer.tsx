import Link from 'next/link'
import { AtSign, Globe, Heart, MessageSquare, Rss } from 'lucide-react'
import { Logo } from '@/components/logo'

const COLUMNS: { heading: string; links: { label: string; href: string }[] }[] = [
  {
    heading: 'Product',
    links: [
      { label: 'Features', href: '/#features' },
      { label: 'Dashboard', href: '/dashboard' },
      { label: 'Pricing', href: '/#pricing' },
      { label: 'Commands', href: '/commands' },
    ],
  },
  {
    heading: 'Resources',
    links: [
      { label: 'Command directory', href: '/commands' },
      { label: 'Support', href: '/commands#support' },
      { label: 'FAQ', href: '/#faq' },
      { label: 'Status', href: '#' },
    ],
  },
  {
    heading: 'Company',
    links: [
      { label: 'About', href: '#' },
      { label: 'Careers', href: '#' },
      { label: 'Contact', href: '#' },
    ],
  },
  {
    heading: 'Legal',
    links: [
      { label: 'Terms of Service', href: '#' },
      { label: 'Privacy Policy', href: '#' },
      { label: 'Acceptable Use', href: '#' },
    ],
  },
]

const SOCIALS = [
  { label: 'Discord', href: '#', icon: MessageSquare },
  { label: 'Website', href: '#', icon: Globe },
  { label: 'Contact', href: '#', icon: AtSign },
  { label: 'Updates', href: '#', icon: Rss },
]

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-surface">
      <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
        <div className="grid gap-10 lg:grid-cols-[1.4fr_repeat(4,1fr)]">
          <div className="space-y-4">
            <Logo />
            <p className="max-w-xs text-sm leading-6 text-muted">
              The moderation records desk for Discord servers — automod, cases, appeals, and
              analytics your whole team works from.
            </p>
            <div className="flex items-center gap-1.5">
              {SOCIALS.map((social) => (
                <a
                  key={social.label}
                  href={social.href}
                  aria-label={social.label}
                  className="focus-ring inline-flex size-9 items-center justify-center rounded-lg border border-border text-muted transition-colors hover:border-accent-line hover:text-foreground"
                >
                  <social.icon className="size-4" aria-hidden />
                </a>
              ))}
            </div>
          </div>

          {COLUMNS.map((column) => (
            <nav key={column.heading} aria-label={column.heading} className="space-y-3.5">
              <p className="text-sm font-semibold text-foreground">{column.heading}</p>
              <ul className="space-y-2.5">
                {column.links.map((link) => (
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
            </nav>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-border pt-6 sm:flex-row">
          <p className="font-mono text-xs text-muted-2">© 2026 Docket. All rights reserved.</p>
          <p className="flex items-center gap-1.5 rounded-full border border-border px-3.5 py-1.5 text-xs text-muted">
            Made with <Heart className="size-3.5 fill-danger text-danger" aria-hidden /> for
            Discord communities
          </p>
        </div>
      </div>
    </footer>
  )
}
