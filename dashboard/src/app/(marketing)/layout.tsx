import { SiteHeader } from '@/components/marketing/site-header'
import { SiteFooter } from '@/components/marketing/site-footer'
import { getCurrentUser } from '@/lib/session'

// The storefront runs in the always-dark "midnight" context — the aurora
// glow treatment of the marketing surface. Scoping the palette here re-skins
// header, footer, and every section via CSS variables without touching the
// dashboard's own light/dark theming.
export default async function MarketingLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser()
  return (
    <div className="midnight flex min-h-full flex-col">
      <SiteHeader user={user ? { name: user.name, email: user.email, avatarUrl: user.avatarUrl, avatarColor: user.avatarColor } : null} />
      <main className="flex-1">{children}</main>
      <SiteFooter />
    </div>
  )
}
