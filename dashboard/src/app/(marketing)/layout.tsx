import Link from 'next/link'
import { ArrowUpRight } from 'lucide-react'
import { Logo } from '@/components/logo'
import { PublicThemeToggle } from '@/components/marketing/theme-toggle'
import { buttonVariants } from '@/components/ui/button'
import { getCurrentUser } from '@/lib/session'

export default async function MarketingLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser()

  return (
    <div className="modern-shell flex min-h-screen flex-col">
      <a
        href="#main-content"
        className="focus-ring fixed left-4 top-4 z-[100] -translate-y-24 rounded-lg bg-foreground px-4 py-2 text-sm font-medium text-paper focus:translate-y-0"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-40 px-3 pt-3 sm:px-5">
        <div className="glass-panel mx-auto flex h-14 w-full max-w-[1440px] items-center rounded-2xl px-3 sm:px-4">
          <Link href="/" aria-label="Docket home" className="focus-ring rounded-lg">
            <Logo />
          </Link>
          <nav className="ml-auto hidden items-center gap-1 md:flex" aria-label="Primary navigation">
            <Link href="/#overview" className="rounded-xl px-3 py-2 text-sm font-medium text-muted hover:bg-surface-2 hover:text-foreground">
              Overview
            </Link>
            <Link href="/#workflow" className="rounded-xl px-3 py-2 text-sm font-medium text-muted hover:bg-surface-2 hover:text-foreground">
              Workflow
            </Link>
            <Link href="/commands" className="rounded-xl px-3 py-2 text-sm font-medium text-muted hover:bg-surface-2 hover:text-foreground">
              Commands
            </Link>
          </nav>
          <div className="ml-auto flex items-center gap-2 md:ml-3">
            <PublicThemeToggle className="rounded-xl" />
            <Link
              href={user ? '/dashboard' : '/api/auth/discord/authorize'}
              className={buttonVariants({ size: 'sm', className: 'hidden sm:inline-flex' })}
            >
              {user ? 'Open dashboard' : 'Sign in with Discord'}
              <ArrowUpRight className="size-4" />
            </Link>
            <Link
              href={user ? '/dashboard' : '/api/auth/discord/authorize'}
              aria-label={user ? 'Open dashboard' : 'Sign in with Discord'}
              className={buttonVariants({ size: 'icon', className: 'sm:hidden' })}
            >
              <ArrowUpRight className="size-4" />
            </Link>
          </div>
        </div>
      </header>
      <main id="main-content" className="flex-1">{children}</main>
      <footer className="border-t border-border bg-surface/55 px-4 py-8">
        <div className="mx-auto flex max-w-[1440px] flex-col items-start justify-between gap-5 sm:flex-row sm:items-center">
          <div>
            <Logo size="sm" />
            <p className="mt-2 text-xs text-muted">A clearer moderation workspace for Discord teams.</p>
          </div>
          <nav className="flex flex-wrap gap-5 text-sm text-muted" aria-label="Footer navigation">
            <Link href="/commands" className="hover:text-foreground">Commands</Link>
            <Link href="/login" className="hover:text-foreground">Sign in</Link>
            <Link href="/dashboard" className="hover:text-foreground">Dashboard</Link>
          </nav>
        </div>
      </footer>
    </div>
  )
}
