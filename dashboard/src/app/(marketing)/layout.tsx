import Link from 'next/link'
import { ArrowUpRight } from 'lucide-react'
import { getCurrentUser } from '@/lib/session'
import styles from './marketing.module.css'

function DocketMark() {
  return (
    <span className={styles.brandMark} aria-hidden="true">
      <span />
      <span />
      <span />
    </span>
  )
}

export default async function MarketingLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser()
  const initials = user?.name
    ?.split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()

  return (
    <div className={styles.layoutShell}>
      <a className={styles.skipLink} href="#main-content">Skip to content</a>
      <header className={styles.siteHeader}>
        <div className={styles.headerInner}>
          <Link className={styles.brand} href="/" aria-label="Docket home">
            <DocketMark />
            <span>DOCKET</span>
          </Link>
          <nav className={styles.nav} aria-label="Primary navigation">
            <Link href="/#workflow">How it works</Link>
            <Link href="/#controls">Controls</Link>
            <Link href="/commands">Commands</Link>
          </nav>
          {user ? (
            <Link className={styles.accountLink} href="/dashboard">
              <span className={styles.avatar}>{initials || 'OP'}</span>
              <span className={styles.accountName}>{user.name}</span>
              <ArrowUpRight aria-hidden="true" size={15} />
            </Link>
          ) : (
            <Link className={styles.signInLink} href="/api/auth/discord/authorize">
              Sign in with Discord
              <ArrowUpRight aria-hidden="true" size={15} />
            </Link>
          )}
        </div>
      </header>
      <main id="main-content" className={styles.main}>{children}</main>
      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <Link className={styles.brand} href="/" aria-label="Docket home">
            <DocketMark />
            <span>DOCKET</span>
          </Link>
          <p>Moderation decisions, kept in order.</p>
          <nav aria-label="Footer navigation">
            <Link href="/commands">Commands</Link>
            <Link href="/login">Sign in</Link>
            <Link href="/dashboard">Dashboard</Link>
          </nav>
        </div>
      </footer>
    </div>
  )
}
