import { redirect } from 'next/navigation'
import { getCurrentUser } from '@/lib/session'
import { PageHeader } from '@/components/dashboard/page-header'
import { AdminNav } from '@/components/dashboard/admin-nav'
import { Badge } from '@/components/ui/badge'

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const user = await getCurrentUser()
  if (!user) redirect('/login')
  if (!user.permissions.includes('admin.access')) redirect('/dashboard')

  return (
    <>
      <PageHeader
        eyebrow="Administration"
        title={
          <span className="flex items-center gap-2">
            Admin <Badge tone="accent">Restricted</Badge>
          </span>
        }
        description="Configure server-wide settings, roles, and features."
      />
      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <aside className="lg:sticky lg:top-20 lg:self-start">
          <AdminNav />
        </aside>
        <div className="min-w-0 space-y-6">{children}</div>
      </div>
    </>
  )
}
