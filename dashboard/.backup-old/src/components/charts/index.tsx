'use client'

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ChartType } from '@/lib/dashboard-config'

const AXIS = { fontSize: 11, fill: 'var(--muted-2)' }

type Point = { label: string; value: number }

function TooltipBox({
  active,
  payload,
  label,
  formatter,
}: {
  active?: boolean
  payload?: { value: number; name?: string; color?: string }[]
  label?: string
  formatter?: (v: number) => string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-lg">
      {label && <p className="mb-1 font-medium text-foreground">{label}</p>}
      {payload.map((p, i) => (
        <p key={i} className="flex items-center gap-1.5 text-muted">
          {p.color && <span className="size-2 rounded-full" style={{ background: p.color }} />}
          {p.name && <span className="capitalize">{p.name}:</span>}
          <span className="font-medium text-foreground">
            {formatter ? formatter(p.value) : p.value.toLocaleString()}
          </span>
        </p>
      ))}
    </div>
  )
}

export function TrendChart({
  data,
  type = 'area',
  height = 260,
  color = 'var(--accent)',
  valueFormatter,
  showAxes = true,
}: {
  data: Point[]
  type?: ChartType
  height?: number
  color?: string
  valueFormatter?: (v: number) => string
  showAxes?: boolean
}) {
  const common = (
    <>
      {showAxes && <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />}
      {showAxes && <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={false} minTickGap={24} />}
      {showAxes && (
        <YAxis
          tick={AXIS}
          tickLine={false}
          axisLine={false}
          width={44}
          tickFormatter={(v) => (valueFormatter ? valueFormatter(v) : String(v))}
        />
      )}
      <Tooltip content={<TooltipBox formatter={valueFormatter} />} cursor={{ stroke: 'var(--border-strong)' }} />
    </>
  )

  return (
    <ResponsiveContainer width="100%" height={height}>
      {type === 'bar' ? (
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          {common}
          <Bar dataKey="value" fill={color} radius={[4, 4, 0, 0]} maxBarSize={40} />
        </BarChart>
      ) : type === 'line' ? (
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          {common}
          <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2.5} dot={false} />
        </LineChart>
      ) : (
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.28} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          {common}
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2.5}
            fill="url(#areaFill)"
          />
        </AreaChart>
      )}
    </ResponsiveContainer>
  )
}

export function GroupedBarChart({
  data,
  keys,
  height = 260,
  valueFormatter,
}: {
  data: Record<string, number | string>[]
  keys: { key: string; color: string; label: string }[]
  height?: number
  valueFormatter?: (v: number) => string
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={false} minTickGap={20} />
        <YAxis tick={AXIS} tickLine={false} axisLine={false} width={44} />
        <Tooltip content={<TooltipBox formatter={valueFormatter} />} cursor={{ fill: 'var(--surface-2)' }} />
        {keys.map((k) => (
          <Bar key={k.key} dataKey={k.key} name={k.label} fill={k.color} radius={[3, 3, 0, 0]} maxBarSize={28} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}

export function DonutChart({
  data,
  height = 220,
  valueFormatter,
}: {
  data: { name: string; value: number; color: string }[]
  height?: number
  valueFormatter?: (v: number) => string
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Tooltip content={<TooltipBox formatter={valueFormatter} />} />
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          innerRadius="58%"
          outerRadius="86%"
          paddingAngle={2}
          stroke="var(--surface)"
          strokeWidth={2}
        >
          {data.map((d) => (
            <Cell key={d.name} fill={d.color} />
          ))}
        </Pie>
      </PieChart>
    </ResponsiveContainer>
  )
}

export function Sparkline({ data, color = 'var(--accent)', height = 40 }: { data: Point[]; color?: string; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey="value" stroke={color} strokeWidth={2} fill="url(#sparkFill)" />
      </AreaChart>
    </ResponsiveContainer>
  )
}
