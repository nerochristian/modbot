import { SiteHeader } from '@/components/marketing/site-header'
import { SiteFooter } from '@/components/marketing/site-footer'

// The marketing storefront runs in the dark "situation room" context — a
// deliberate contrast with the calm light records-desk of the app itself.
// Scoping the palette here re-skins header, footer, and every section via
// CSS variables without touching the dashboard.
export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="situation flex min-h-full flex-col bg-paper">
      <SiteHeader />
      <main className="flex-1">{children}</main>
      <SiteFooter />
    </div>
  )
}
