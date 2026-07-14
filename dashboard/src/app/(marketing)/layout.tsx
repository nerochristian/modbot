import { SiteHeader } from "@/components/marketing/site-header";
import { SiteFooter } from "@/components/marketing/site-footer";
import { getCurrentUser } from "@/lib/session";

// The marketing storefront runs in the dark "situation room" context — a
// deliberate contrast with the calm light records-desk of the app itself.
// Scoping the palette here re-skins header, footer, and every section via
// CSS variables without touching the dashboard.
export default async function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const user = await getCurrentUser();
  return (
    <div className="situation modern-marketing flex min-h-full flex-col">
      <SiteHeader
        user={
          user
            ? {
                name: user.name,
                email: user.email,
                avatarUrl: user.avatarUrl,
                avatarColor: user.avatarColor,
              }
            : null
        }
      />
      <main className="flex-1">{children}</main>
      <SiteFooter />
    </div>
  );
}
