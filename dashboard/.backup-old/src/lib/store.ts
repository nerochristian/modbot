'use client'

import { create } from 'zustand'
import {
  DEFAULT_DASHBOARD_CONFIG,
  accentValue,
  type ChartType,
  type DashboardConfig,
  type Density,
  type ExportFormat,
  type ThemeMode,
  type DateRange,
  type WidgetPref,
} from '@/lib/dashboard-config'
import type { Permission, Role } from '@/lib/rbac'

export type SessionUser = {
  id: string
  name: string
  email: string
  role: Role
  avatarColor: string
  title: string | null
  permissions: Permission[]
}

type ConfigState = {
  ready: boolean
  user: SessionUser | null
  config: DashboardConfig
  savedAt: number

  hydrate: (config: DashboardConfig, user: SessionUser) => void
  patch: (partial: Partial<DashboardConfig>) => void
  setTheme: (theme: ThemeMode) => void
  setAccent: (accent: string) => void
  setDensity: (density: Density) => void
  setSidebarCollapsed: (collapsed: boolean) => void
  toggleSidebar: () => void
  setRefreshInterval: (seconds: number) => void
  setDefaultLandingPage: (page: string) => void
  setExportFormat: (format: ExportFormat) => void
  setDateRange: (range: DateRange) => void
  setWidgets: (widgets: WidgetPref[]) => void
  updateWidget: (key: string, changes: Partial<WidgetPref>) => void
  setWidgetChartType: (key: string, chartType: ChartType) => void
  setTableColumns: (page: string, columns: string[]) => void
  setNotificationPref: (
    group: keyof DashboardConfig['notifications'],
    channel: 'email' | 'push' | 'inApp',
    value: boolean,
  ) => void
  can: (permission: Permission) => boolean
}

/** Push theme/accent/density to the DOM + localStorage for no-flash reloads. */
export function applyTheme(config: DashboardConfig) {
  if (typeof document === 'undefined') return
  const el = document.documentElement
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const dark = config.theme === 'dark' || (config.theme === 'system' && prefersDark)
  el.classList.toggle('dark', dark)
  el.style.setProperty('--accent', accentValue(config.accent))
  el.setAttribute('data-density', config.density)
  try {
    localStorage.setItem('nebula-theme', config.theme)
    localStorage.setItem('nebula-accent', accentValue(config.accent))
    localStorage.setItem('nebula-density', config.density)
  } catch {
    /* ignore quota / privacy-mode errors */
  }
}

export const useConfigStore = create<ConfigState>((set, get) => {
  // Update state, re-apply theme, and mark dirty so the provider persists it.
  const commit = (config: DashboardConfig) => {
    applyTheme(config)
    set({ config, savedAt: Date.now() })
  }

  return {
    ready: false,
    user: null,
    config: DEFAULT_DASHBOARD_CONFIG,
    savedAt: 0,

    hydrate: (config, user) => {
      applyTheme(config)
      set({ config, user, ready: true })
    },
    patch: (partial) => commit({ ...get().config, ...partial }),
    setTheme: (theme) => commit({ ...get().config, theme }),
    setAccent: (accent) => commit({ ...get().config, accent }),
    setDensity: (density) => commit({ ...get().config, density }),
    setSidebarCollapsed: (sidebarCollapsed) => commit({ ...get().config, sidebarCollapsed }),
    toggleSidebar: () =>
      commit({ ...get().config, sidebarCollapsed: !get().config.sidebarCollapsed }),
    setRefreshInterval: (refreshInterval) => commit({ ...get().config, refreshInterval }),
    setDefaultLandingPage: (defaultLandingPage) =>
      commit({ ...get().config, defaultLandingPage }),
    setExportFormat: (exportFormat) => commit({ ...get().config, exportFormat }),
    setDateRange: (dateRange) => commit({ ...get().config, dateRange }),
    setWidgets: (widgets) => commit({ ...get().config, widgets }),
    updateWidget: (key, changes) =>
      commit({
        ...get().config,
        widgets: get().config.widgets.map((w) => (w.key === key ? { ...w, ...changes } : w)),
      }),
    setWidgetChartType: (key, chartType) =>
      commit({
        ...get().config,
        widgets: get().config.widgets.map((w) => (w.key === key ? { ...w, chartType } : w)),
      }),
    setTableColumns: (page, columns) =>
      commit({
        ...get().config,
        tableColumns: { ...get().config.tableColumns, [page]: columns },
      }),
    setNotificationPref: (group, channel, value) =>
      commit({
        ...get().config,
        notifications: {
          ...get().config.notifications,
          [group]: { ...get().config.notifications[group], [channel]: value },
        },
      }),
    can: (permission) => !!get().user?.permissions.includes(permission),
  }
})
