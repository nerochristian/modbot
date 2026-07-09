/**
 * Dashboard configuration model.
 *
 * A single JSON blob per user (DashboardConfig.config) drives every
 * customization surface: theme, accent, density, sidebar state, refresh cadence,
 * default landing page, export format, per-widget visibility/order/chart-type,
 * per-table visible columns, and notification preferences. Defaults here are the
 * baseline applied to new users and used when a stored config is missing keys.
 */

export type ThemeMode = 'light' | 'dark' | 'system'
export type Density = 'comfortable' | 'compact'
export type ChartType = 'line' | 'area' | 'bar'
export type ExportFormat = 'csv' | 'json' | 'xlsx' | 'pdf'
export type DateRange = '7d' | '30d' | '90d' | '12m'

export type NotificationChannelPrefs = {
  email: boolean
  push: boolean
  inApp: boolean
}

export type WidgetPref = {
  key: string
  visible: boolean
  order: number
  chartType?: ChartType
}

export type DashboardConfig = {
  theme: ThemeMode
  accent: string
  density: Density
  sidebarCollapsed: boolean
  refreshInterval: number // seconds; 0 = off
  defaultLandingPage: string
  exportFormat: ExportFormat
  dateRange: DateRange
  widgets: WidgetPref[]
  tableColumns: Record<string, string[]>
  notifications: {
    billing: NotificationChannelPrefs
    security: NotificationChannelPrefs
    product: NotificationChannelPrefs
    mentions: NotificationChannelPrefs
  }
}

export const ACCENT_COLORS: { key: string; label: string; value: string }[] = [
  { key: 'indigo', label: 'Indigo', value: '#6366f1' },
  { key: 'violet', label: 'Violet', value: '#8b5cf6' },
  { key: 'blue', label: 'Blue', value: '#3b82f6' },
  { key: 'sky', label: 'Sky', value: '#0ea5e9' },
  { key: 'emerald', label: 'Emerald', value: '#10b981' },
  { key: 'amber', label: 'Amber', value: '#f59e0b' },
  { key: 'rose', label: 'Rose', value: '#f43f5e' },
  { key: 'pink', label: 'Pink', value: '#ec4899' },
]

export function accentValue(key: string): string {
  return ACCENT_COLORS.find((c) => c.key === key)?.value ?? ACCENT_COLORS[0].value
}

export const REFRESH_INTERVALS: { label: string; value: number }[] = [
  { label: 'Off', value: 0 },
  { label: '15 seconds', value: 15 },
  { label: '30 seconds', value: 30 },
  { label: '1 minute', value: 60 },
  { label: '5 minutes', value: 300 },
]

export const DATE_RANGES: { label: string; value: DateRange; days: number }[] = [
  { label: 'Last 7 days', value: '7d', days: 7 },
  { label: 'Last 30 days', value: '30d', days: 30 },
  { label: 'Last 90 days', value: '90d', days: 90 },
  { label: 'Last 12 months', value: '12m', days: 365 },
]

export function rangeDays(range: DateRange): number {
  return DATE_RANGES.find((r) => r.value === range)?.days ?? 30
}

/** The catalog of overview widgets a user can arrange. Mirrors the Widget table. */
export const WIDGET_CATALOG: {
  key: string
  name: string
  description: string
  category: string
  chartType?: ChartType
  defaultVisible: boolean
}[] = [
  { key: 'kpi-revenue', name: 'Revenue', description: 'Monthly recurring revenue KPI', category: 'kpi', defaultVisible: true },
  { key: 'kpi-users', name: 'Active users', description: 'Active users KPI', category: 'kpi', defaultVisible: true },
  { key: 'kpi-conversion', name: 'Conversion rate', description: 'Trial-to-paid conversion KPI', category: 'kpi', defaultVisible: true },
  { key: 'kpi-churn', name: 'Churn rate', description: 'Monthly churn KPI', category: 'kpi', defaultVisible: true },
  { key: 'chart-revenue', name: 'Revenue over time', description: 'Revenue trend chart', category: 'chart', chartType: 'area', defaultVisible: true },
  { key: 'chart-growth', name: 'User growth', description: 'New vs. churned users', category: 'chart', chartType: 'bar', defaultVisible: true },
  { key: 'chart-retention', name: 'Retention', description: 'Cohort retention curve', category: 'chart', chartType: 'line', defaultVisible: true },
  { key: 'list-activity', name: 'Recent activity', description: 'Latest team activity feed', category: 'list', defaultVisible: true },
  { key: 'list-customers', name: 'Top customers', description: 'Highest-revenue customers', category: 'list', defaultVisible: true },
  { key: 'chart-plans', name: 'Plan distribution', description: 'Customers by plan', category: 'chart', chartType: 'bar', defaultVisible: true },
  { key: 'status-system', name: 'System status', description: 'Service health indicators', category: 'status', defaultVisible: true },
  { key: 'chart-traffic', name: 'Traffic sources', description: 'Acquisition channels', category: 'chart', chartType: 'bar', defaultVisible: false },
]

export const DEFAULT_TABLE_COLUMNS: Record<string, string[]> = {
  customers: ['name', 'company', 'plan', 'status', 'mrr', 'country', 'lastActiveAt'],
  users: ['name', 'email', 'role', 'status', 'lastLoginAt'],
  reports: ['name', 'type', 'status', 'format', 'createdAt'],
}

const defaultChannel: NotificationChannelPrefs = { email: true, push: false, inApp: true }

export const DEFAULT_DASHBOARD_CONFIG: DashboardConfig = {
  theme: 'dark',
  accent: 'iris',
  density: 'compact',
  sidebarCollapsed: false,
  refreshInterval: 0,
  defaultLandingPage: '/dashboard',
  exportFormat: 'csv',
  dateRange: '30d',
  widgets: WIDGET_CATALOG.map((w, i) => ({
    key: w.key,
    visible: w.defaultVisible,
    order: i,
    chartType: w.chartType,
  })),
  tableColumns: DEFAULT_TABLE_COLUMNS,
  notifications: {
    billing: { ...defaultChannel },
    security: { email: true, push: true, inApp: true },
    product: { ...defaultChannel },
    mentions: { ...defaultChannel },
  },
}

/** Merge a stored (possibly partial/legacy) config onto current defaults. */
export function mergeConfig(partial: Partial<DashboardConfig> | null | undefined): DashboardConfig {
  if (!partial) return structuredClone(DEFAULT_DASHBOARD_CONFIG)
  return {
    ...DEFAULT_DASHBOARD_CONFIG,
    ...partial,
    widgets:
      partial.widgets && partial.widgets.length > 0
        ? reconcileWidgets(partial.widgets)
        : DEFAULT_DASHBOARD_CONFIG.widgets,
    tableColumns: { ...DEFAULT_TABLE_COLUMNS, ...(partial.tableColumns ?? {}) },
    notifications: { ...DEFAULT_DASHBOARD_CONFIG.notifications, ...(partial.notifications ?? {}) },
  }
}

/** Ensure every catalog widget is represented, preserving stored prefs. */
function reconcileWidgets(stored: WidgetPref[]): WidgetPref[] {
  const byKey = new Map(stored.map((w) => [w.key, w]))
  return WIDGET_CATALOG.map((w, i) => {
    const existing = byKey.get(w.key)
    return (
      existing ?? { key: w.key, visible: w.defaultVisible, order: i, chartType: w.chartType }
    )
  }).sort((a, b) => a.order - b.order)
}
