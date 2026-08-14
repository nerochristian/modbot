import { PageHeader } from '@/components/dashboard/page-header'
import { SettingsNav } from '@/components/dashboard/settings-nav'

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <PageHeader eyebrow="Workspace" title="Settings" description="Manage your Discord sessions and dashboard preferences." />
      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <aside className="lg:sticky lg:top-20 lg:self-start">
          <SettingsNav />
        </aside>
        <div className="min-w-0 space-y-6">{children}</div>
      </div>
    </>
  )
}
