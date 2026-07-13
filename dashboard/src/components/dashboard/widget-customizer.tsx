'use client'

import { ChevronUp, ChevronDown, GripVertical } from 'lucide-react'
import { Modal } from '@/components/ui/modal'
import { Switch } from '@/components/ui/switch'
import { SegmentedControl } from '@/components/ui/segmented'
import { useConfigStore } from '@/lib/store'
import { WIDGET_CATALOG, type ChartType } from '@/lib/dashboard-config'

const CATALOG_BY_KEY = Object.fromEntries(WIDGET_CATALOG.map((w) => [w.key, w]))
const SUPPORTS_CHART_TYPE = new Set(['chart-actions', 'chart-joins'])

export function WidgetCustomizer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const widgets = useConfigStore((s) => s.config.widgets)
  const setWidgets = useConfigStore((s) => s.setWidgets)
  const updateWidget = useConfigStore((s) => s.updateWidget)
  const setWidgetChartType = useConfigStore((s) => s.setWidgetChartType)

  const ordered = [...widgets].sort((a, b) => a.order - b.order)

  function move(index: number, dir: -1 | 1) {
    const next = [...ordered]
    const target = index + dir
    if (target < 0 || target >= next.length) return
    ;[next[index], next[target]] = [next[target], next[index]]
    setWidgets(next.map((w, i) => ({ ...w, order: i })))
  }

  const visibleCount = ordered.filter((w) => w.visible).length

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Customize dashboard"
      description="Show, hide, reorder widgets, and choose chart types. Changes save automatically."
      size="lg"
    >
      <p className="mb-3 text-xs text-muted">
        {visibleCount} of {ordered.length} widgets visible
      </p>
      <ul className="space-y-2">
        {ordered.map((w, i) => {
          const meta = CATALOG_BY_KEY[w.key]
          if (!meta) return null
          const displayName = w.key === 'chart-channels' ? 'Active channels' : meta.name
          const displayDescription = w.key === 'chart-channels'
            ? 'Channels ranked by recorded message volume'
            : meta.description
          return (
            <li
              key={w.key}
              className="flex items-center gap-3 rounded-xl border border-border bg-surface px-3 py-2.5"
            >
              <div className="flex flex-col">
                <button
                  onClick={() => move(i, -1)}
                  disabled={i === 0}
                  className="focus-ring rounded p-0.5 text-muted-2 hover:text-foreground disabled:opacity-30"
                  aria-label="Move up"
                >
                  <ChevronUp className="size-4" />
                </button>
                <button
                  onClick={() => move(i, 1)}
                  disabled={i === ordered.length - 1}
                  className="focus-ring rounded p-0.5 text-muted-2 hover:text-foreground disabled:opacity-30"
                  aria-label="Move down"
                >
                  <ChevronDown className="size-4" />
                </button>
              </div>
              <GripVertical className="size-4 shrink-0 text-muted-2" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-foreground">{displayName}</p>
                <p className="truncate text-xs text-muted">{displayDescription}</p>
              </div>
              {SUPPORTS_CHART_TYPE.has(w.key) && w.visible && (
                <SegmentedControl
                  size="sm"
                  aria-label={`${displayName} chart type`}
                  value={(w.chartType ?? 'area') as ChartType}
                  onChange={(v) => setWidgetChartType(w.key, v)}
                  options={[
                    { label: 'Area', value: 'area' },
                    { label: 'Line', value: 'line' },
                    { label: 'Bar', value: 'bar' },
                  ]}
                />
              )}
              <Switch
                checked={w.visible}
                onChange={(v) => updateWidget(w.key, { visible: v })}
                label={`Toggle ${displayName}`}
              />
            </li>
          )
        })}
      </ul>
    </Modal>
  )
}
