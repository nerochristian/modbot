import { SiteHeader } from '@/components/marketing/site-header'
import { SiteFooter } from '@/components/marketing/site-footer'
import { getCurrentUser } from '@/lib/session'

// The storefront wears the product's own identity — the calm porcelain
// records desk — rather than a separate dark costume. One brand, one palette:
// what the landing page promises is literally what the console looks like.
export default async function MarketingLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser()
  return (
    <div className="flex min-h-full flex-col bg-paper">
      <SiteHeader user={user ? { name: user.name, email: user.email, avatarUrl: user.avatarUrl, avatarColor: user.avatarColor } : null} />
      <main className="flex-1">{children}</main>
      <SiteFooter />
    </div>
  )
}
