'use client'

import { SettingsCard, SettingRow } from '@/components/dashboard/setting-section'
import { Select } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { useConfigStore } from '@/lib/store'
import { NAV_ITEMS } from '@/lib/nav'
import { REFRESH_INTERVALS, DATE_RANGES, type DateRange, type ExportFormat } from '@/lib/dashboard-config'

export default function DashboardPreferencesPage() {
  const config = useConfigStore((s) => s.config)
  const permissions = useConfigStore((s) => s.user?.permissions ?? [])
  const setDefaultLandingPage = useConfigStore((s) => s.setDefaultLandingPage)
  const setSidebarCollapsed = useConfigStore((s) => s.setSidebarCollapsed)
  const setRefreshInterval = useConfigStore((s) => s.setRefreshInterval)
  const setExportFormat = useConfigStore((s) => s.setExportFormat)
  const setDateRange = useConfigStore((s) => s.setDateRange)

  const landingOptions = NAV_ITEMS.filter((i) => permissions.includes(i.permission)).map((i) => ({
    label: i.label,
    value: i.href,
  }))

  return (
    <SettingsCard
      title="Dashboard preferences"
      description="Control default behavior across your dashboard. Changes save automatically."
    >
      <div className="divide-y divide-border">
        <SettingRow label="Default landing page" description="Where you land after signing in.">
          <Select
            className="w-56"
            options={landingOptions}
            value={config.defaultLandingPage}
            onChange={(e) => setDefaultLandingPage(e.target.value)}
          />
        </SettingRow>

        <SettingRow label="Default date range" description="Applied to analytics and overview charts.">
          <Select
            className="w-56"
            options={DATE_RANGES.map((r) => ({ label: r.label, value: r.value }))}
            value={config.dateRange}
            onChange={(e) => setDateRange(e.target.value as DateRange)}
          />
        </SettingRow>

        <SettingRow label="Auto-refresh" description="How often dashboard data refreshes automatically.">
          <Select
            className="w-56"
            options={REFRESH_INTERVALS.map((r) => ({ label: r.label, value: String(r.value) }))}
            value={String(config.refreshInterval)}
            onChange={(e) => setRefreshInterval(Number(e.target.value))}
          />
        </SettingRow>

        <SettingRow label="Default export format" description="Used by export buttons across the app.">
          <Select
            className="w-56"
            options={[
              { label: 'CSV', value: 'csv' },
              { label: 'JSON', value: 'json' },
            ]}
            value={config.exportFormat === 'json' ? 'json' : 'csv'}
            onChange={(e) => setExportFormat(e.target.value as ExportFormat)}
          />
        </SettingRow>

        <SettingRow label="Collapse sidebar by default" description="Start with a compact, icon-only sidebar.">
          <Switch checked={config.sidebarCollapsed} onChange={setSidebarCollapsed} label="Collapse sidebar" />
        </SettingRow>
      </div>
    </SettingsCard>
  )
}
