import {
  Activity, AlertTriangle, ArchiveRestore, Ban, Calendar, CheckCircle2,
  Clock, Database, Download, FileText, Filter, Gavel, Hash,
  Lock, MessageSquare, Plug, RefreshCcw, Save, Search, Shield,
  ShieldAlert, ShieldCheck, SlidersHorizontal, Star, Trash2, UserMinus,
  Users, Zap
} from 'lucide-react'
import { useGuild } from './GuildContext'

const statRows = {
  dashboard: [
    ['Server Health', 'Excellent', '100/100', ShieldCheck, '#10b981'],
    ['Members', '12,842', '+5.23%', Users, 'var(--brand-primary)'],
    ['Messages (24h)', '18,392', '+12.45%', MessageSquare, 'var(--info)'],
    ['Threats Blocked', '247', '+18.6%', Shield, 'var(--success)'],
    ['Active Cases', '18', '-5', Gavel, 'var(--warning)'],
    ['Uptime', '99.99%', 'Operational', CheckCircle2, 'var(--success)'],
  ],
  events: [
    ['Total Events', '24,892', '+18.7%', Activity, 'var(--brand-primary)'],
    ['Security Events', '492', '+21.4%', Shield, 'var(--success)'],
    ['Moderation Actions', '1,842', '+14.9%', Gavel, 'var(--warning)'],
    ['Users Affected', '3,128', '+9.3%', Users, 'var(--info)'],
    ['Critical Events', '38', '+26.7%', AlertTriangle, 'var(--error)'],
    ['Events Per Hour', '103', 'Live average', Clock, 'var(--brand-primary)'],
  ],
  logs: [
    ['Total Logs', '34,782', '+18.6%', FileText, 'var(--brand-primary)'],
    ['Deleted Messages', '12,842', '+23.7%', Trash2, 'var(--error)'],
    ['Member Actions', '8,621', '+12.4%', Users, 'var(--warning)'],
    ['Automod Actions', '6,247', '+15.3%', ShieldAlert, 'var(--info)'],
    ['Channel Updates', '3,072', '+8.7%', Hash, 'var(--info)'],
    ['Role Changes', '3,998', '+11.2%', ShieldCheck, 'var(--success)'],
  ],
}

const timeline = [
  ['15:42:18', 'Raid attempt blocked', 'AutoMod blocked 15 suspicious joins', 'High', 'var(--error)'],
  ['15:41:33', 'Message deleted', 'Inappropriate content detected', 'Medium', 'var(--warning)'],
  ['15:40:07', 'User warned', 'Reason: Spam', 'Low', 'var(--info)'],
  ['15:38:51', 'Channel locked', 'Raid protection enabled', 'High', 'var(--error)'],
  ['15:36:45', 'Mass mentions detected', '15+ users mentioned', 'Medium', 'var(--warning)'],
  ['15:34:01', 'Backup completed', 'Server channels and roles saved', 'Info', 'var(--success)'],
]

function PageHeader({ title, subtitle, actions = true }) {
  return (
    <div className="vtx-page-header">
      <div>
        <h1 className="vtx-page-title">{title}</h1>
        <p className="vtx-page-subtitle">{subtitle}</p>
      </div>
      {actions && (
        <div className="vtx-header-actions">
          <button className="btn btn-secondary btn-sm"><Zap size={14} /> Quick Actions</button>
          <button className="btn btn-secondary btn-sm"><Calendar size={14} /> May 17 - May 24</button>
          <button className="btn btn-primary btn-sm">+ Add Widget</button>
        </div>
      )}
    </div>
  )
}

function StatStrip({ type = 'dashboard' }) {
  return (
    <div className="vtx-stats-row vtx-stats-row-wide">
      {statRows[type].map(([label, value, trend, Icon, color]) => (
        <div className="vtx-stat-card" key={label}>
          <div className="vtx-sc-top">
            <span className="vtx-sc-lbl">{label}</span>
            <div className="vtx-sc-icon" style={{ background: `${color}18`, color }}>
              <Icon size={18} />
            </div>
          </div>
          <div className="vtx-sc-val">{value}</div>
          <div className={trend.startsWith('-') ? 'vtx-sc-trend vtx-trend-down' : 'vtx-sc-trend vtx-trend-up'}>
            {trend}
            {!trend.includes('Operational') && !trend.includes('average') && <span className="vtx-trend-lbl"> vs last 7 days</span>}
          </div>
        </div>
      ))}
    </div>
  )
}

function Sparkline({ color = 'var(--brand-primary)', values = [22, 48, 42, 66, 58, 83, 61, 74, 49, 70, 62, 88] }) {
  const max = Math.max(...values)
  const points = values.map((value, index) => `${(index / (values.length - 1)) * 100},${100 - (value / max) * 92}`).join(' ')

  return (
    <div className="vtx-mini-chart">
      <svg viewBox="0 0 100 100" preserveAspectRatio="none">
        <polygon points={`0,100 ${points} 100,100`} fill={color} opacity="0.14" />
        <polyline points={points} fill="none" stroke={color} strokeWidth="2.2" />
      </svg>
    </div>
  )
}

function TimelinePanel({ title = 'Activity Timeline' }) {
  return (
    <div className="vtx-bento-card vtx-timeline-card">
      <div className="vtx-bc-header">
        <h3>{title}</h3>
        <span className="vtx-live-dot">Live</span>
      </div>
      <div className="vtx-event-stream">
        {timeline.map(([time, label, detail, severity, color]) => (
          <div className="vtx-event-row" key={`${time}-${label}`}>
            <span className="vtx-event-time">{time}</span>
            <span className="vtx-event-icon" style={{ color, background: `${color}16` }}><AlertTriangle size={14} /></span>
            <span className="vtx-event-copy"><strong>{label}</strong><small>{detail}</small></span>
            <span className="vtx-severity" style={{ color, background: `${color}16`, borderColor: `${color}33` }}>{severity}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function QuickActions() {
  const actions = [
    [AlertTriangle, 'Warn User', 'var(--warning)'],
    [UserMinus, 'Mute User', 'var(--brand-primary)'],
    [Ban, 'Ban User', 'var(--error)'],
    [FileText, 'Add Note', 'var(--info)'],
    [Lock, 'Lock Channel', 'var(--warning)'],
    [Trash2, 'Clear Chat', 'var(--error)'],
  ]

  return (
    <div className="vtx-bento-card">
      <div className="vtx-bc-header"><h3>Quick Actions</h3></div>
      <div className="vtx-action-grid">
        {actions.map(([Icon, label, color]) => (
          <button className="vtx-action-button" key={label}>
            <Icon size={18} style={{ color }} />
            <span>{label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

function DonutSummary({ title = 'Automation Summary' }) {
  return (
    <div className="vtx-bento-card">
      <div className="vtx-bc-header"><h3>{title}</h3><span className="vtx-bc-link">View All</span></div>
      <div className="vtx-ring-summary">
        <div className="vtx-ring">
          <span>892</span>
          <small>Actions</small>
        </div>
        <div className="vtx-ring-list">
          {[
            ['Spam Filter', '412', 'var(--brand-primary)'],
            ['Link Filter', '213', 'var(--warning)'],
            ['Anti-Raid', '156', 'var(--info)'],
            ['Word Filter', '89', 'var(--success)'],
            ['Other', '22', 'var(--text-muted)'],
          ].map(([label, value, color]) => (
            <div key={label}><span style={{ background: color }} />{label}<strong>{value}</strong></div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function CommandCenter() {
  const { guild } = useGuild()

  return (
    <div className="vtx-overview">
      <PageHeader title={`Welcome back${guild?.name ? `, ${guild.name}` : ''}`} subtitle="Here is what is happening in your community right now." />
      <StatStrip type="dashboard" />
      <div className="vtx-dashboard-grid">
        <div className="vtx-bento-card vtx-map-card col-span-2">
          <div className="vtx-bc-header">
            <h3>Live Threat Map</h3>
            <div className="vtx-map-legend"><span /> Low <span /> Medium <span /> High</div>
          </div>
          <div className="vtx-threat-map">
            {['North America', 'Europe', 'Brazil', 'East Asia', 'Australia'].map((label, index) => (
              <span className={`vtx-map-node node-${index + 1}`} key={label} title={label} />
            ))}
          </div>
        </div>
        <TimelinePanel />
        <QuickActions />
        <DonutSummary />
        <div className="vtx-bento-card col-span-2">
          <div className="vtx-bc-header"><h3>Member Activity Heatmap</h3><span className="vtx-bc-link">Last 7 Days</span></div>
          <div className="vtx-heatmap">
            {Array.from({ length: 168 }, (_, index) => <span key={index} style={{ opacity: 0.15 + ((index * 17) % 85) / 100 }} />)}
          </div>
        </div>
        <SystemOverview />
        <ScheduledTasks />
      </div>
    </div>
  )
}

export function EventsDashboard() {
  return (
    <div className="vtx-overview">
      <PageHeader title="Events" subtitle="Real-time event monitoring and activity feed across your server." />
      <StatStrip type="events" />
      <div className="vtx-dashboard-grid">
        <TimelinePanel title="Event Stream" />
        <div className="vtx-bento-card col-span-2"><div className="vtx-bc-header"><h3>Event Volume</h3><span className="vtx-bc-link">Last 7 Days</span></div><Sparkline values={[0, 42, 51, 66, 48, 78, 72, 33, 70, 83, 42, 69]} /></div>
        <DonutSummary title="Events by Category" />
        <SeverityPanel />
        <CompactList title="Recent Joins" icon={Users} items={['GalaxyWolf', 'StarGazer', 'LunarKnight', 'CosmicRay', 'NebulaX']} />
        <CompactList title="Recent Leaves" icon={UserMinus} items={['ShadowRealm', 'VoidWalker', 'DarkMatter', 'GhostProtocol', 'SilentEcho']} danger />
        <SecurityIncidents />
      </div>
    </div>
  )
}

export function LogsDashboard() {
  return (
    <div className="vtx-overview">
      <PageHeader title="Logs" subtitle="Comprehensive audit logs and server activity history." />
      <StatStrip type="logs" />
      <div className="vtx-dashboard-grid">
        <div className="vtx-bento-card col-span-3">
          <div className="vtx-tabs"><span className="active">All Logs</span><span>Deleted Messages</span><span>Member Actions</span><span>Role Changes</span><span>AutoMod Actions</span></div>
          <Sparkline values={[28, 62, 51, 44, 69, 34, 55, 80, 72, 88, 63, 39, 70, 52]} />
        </div>
        <LogDetails />
        <LogTable />
      </div>
    </div>
  )
}

export function AntiRaidDashboard() {
  return (
    <ModuleDashboard
      title="Anti-Raid"
      subtitle="Detect mass joins, suspicious accounts, and coordinated attacks before they spread."
      icon={ShieldAlert}
      color="#ef4444"
      stats={[['Raids Blocked', '2'], ['Suspicious Joins', '38'], ['Lockdowns', '4'], ['Protected Members', '12,842']]}
      modules={['Join rate detection', 'Account age gate', 'Mass mention response', 'Auto lockdown', 'Invite quarantine', 'Raid recovery']}
    />
  )
}

export function ModerationDashboard() {
  return (
    <ModuleDashboard
      title="Moderation"
      subtitle="Run staff actions, review active cases, and track moderator output."
      icon={Gavel}
      color="var(--brand-primary)"
      stats={[['Active Cases', '18'], ['Actions Today', '392'], ['Avg Response', '42s'], ['Staff Online', '24']]}
      modules={['Warn workflow', 'Timeout presets', 'Case notes', 'Mod leaderboard', 'Escalation rules', 'Evidence capture']}
    />
  )
}

export function MembersDashboard() {
  return (
    <ModuleDashboard
      title="Members"
      subtitle="Monitor joins, leaves, risk score, roles, and member activity."
      icon={Users}
      color="var(--info)"
      stats={[['Members', '12,842'], ['Joined Today', '156'], ['Left Today', '89'], ['Flagged', '42']]}
      modules={['Join analytics', 'Role distribution', 'Risk scoring', 'Inactive members', 'New member queue', 'Account age segments']}
    />
  )
}

export function WarningsDashboard() {
  return (
    <ModuleDashboard
      title="Warnings"
      subtitle="Review warning trends, repeat offenders, and configured escalation thresholds."
      icon={AlertTriangle}
      color="var(--warning)"
      stats={[['Warnings', '454'], ['Repeat Users', '37'], ['Escalated', '18'], ['Resolved', '92%']]}
      modules={['Warning rules', 'Strike decay', 'Escalations', 'Appeal links', 'Moderator notes', 'Repeat detection']}
    />
  )
}

export function AppealsDashboard() {
  return (
    <ModuleDashboard
      title="Appeals"
      subtitle="Manage moderation appeals, review evidence, and track resolution speed."
      icon={RefreshCcw}
      color="#10b981"
      stats={[['Open Appeals', '12'], ['Approved', '38%'], ['Denied', '54%'], ['Avg Review', '3h']]}
      modules={['Appeal queue', 'Evidence viewer', 'Staff voting', 'Decision notes', 'DM notifications', 'Case linking']}
    />
  )
}

export function BackupDashboard() {
  return (
    <ModuleDashboard
      title="Server Backup"
      subtitle="Backup channels, roles, permissions, and automations with restore checkpoints."
      icon={Database}
      color="var(--info)"
      stats={[['Backups', '28'], ['Last Backup', '2m'], ['Restore Points', '14'], ['Coverage', '100%']]}
      modules={['Role snapshots', 'Channel tree', 'Permission diff', 'Scheduled backups', 'One-click restore', 'Export archive']}
    />
  )
}

export function IntegrationsDashboard() {
  return (
    <ModuleDashboard
      title="Integrations"
      subtitle="Connect Vortex to support tools, audit sinks, webhooks, and automation pipelines."
      icon={Plug}
      color="var(--brand-primary)"
      stats={[['Connected', '8'], ['Webhooks', '12'], ['Failures', '0'], ['Sync Health', '99%']]}
      modules={['Discord webhooks', 'Audit exports', 'Support bridge', 'AI provider', 'Status page', 'Custom API']}
    />
  )
}

export function PremiumDashboard() {
  return (
    <div className="vtx-overview">
      <PageHeader title="Premium" subtitle="Unlock advanced protection, higher automation limits, and priority workflows." actions={false} />
      <div className="vtx-premium-hero">
        <div>
          <div className="vtx-premium-mark"><Star size={28} /></div>
          <h2>Vortex Premium</h2>
          <p>Advanced anti-raid responses, unlimited server backups, detailed analytics, AI moderation upgrades, and priority support for serious communities.</p>
          <button className="btn btn-primary btn-lg"><Star size={16} /> Upgrade Server</button>
        </div>
        <div className="vtx-premium-grid">
          {['Advanced Anti-Raid', 'Unlimited Backups', 'AI Moderation', 'Priority Support', 'Audit Exports', 'Custom Branding'].map(item => (
            <div key={item}><CheckCircle2 size={16} />{item}</div>
          ))}
        </div>
      </div>
    </div>
  )
}

function ModuleDashboard({ title, subtitle, icon: Icon, color, stats, modules }) {
  return (
    <div className="vtx-overview">
      <PageHeader title={title} subtitle={subtitle} />
      <div className="vtx-module-hero" style={{ '--module-color': color }}>
        <div className="vtx-module-icon"><Icon size={28} /></div>
        <div><h2>{title} Control Center</h2><p>{subtitle}</p></div>
        <button className="btn btn-primary btn-sm"><SlidersHorizontal size={14} /> Configure</button>
      </div>
      <div className="vtx-module-stats">
        {stats.map(([label, value]) => <div className="vtx-stat-card" key={label}><span className="vtx-sc-lbl">{label}</span><strong>{value}</strong><small>Live metric</small></div>)}
      </div>
      <div className="vtx-dashboard-grid">
        <div className="vtx-bento-card col-span-2"><div className="vtx-bc-header"><h3>{title} Activity</h3><span className="vtx-bc-link">Last 7 Days</span></div><Sparkline color={color} /></div>
        <TimelinePanel title="Recent Activity" />
        <div className="vtx-bento-card">
          <div className="vtx-bc-header"><h3>Controls</h3><span className="vtx-bc-link">Edit</span></div>
          <div className="vtx-control-list">
            {modules.map(module => <div key={module}><span>{module}</span><button className="mp-toggle on"><span className="mp-toggle-thumb" /></button></div>)}
          </div>
        </div>
        <CompactList title="Recent Records" icon={Icon} items={modules.slice(0, 5)} />
        <SystemOverview />
      </div>
    </div>
  )
}

function CompactList({ title, icon: Icon, items, danger = false }) {
  return (
    <div className="vtx-bento-card">
      <div className="vtx-bc-header"><h3>{title}</h3><span className="vtx-bc-link">View All</span></div>
      <div className="vtx-compact-list">
        {items.map((item, index) => (
          <div key={item}>
            <span className="vtx-avatar-dot" data-danger={danger}><Icon size={12} /></span>
            <strong>{item}</strong>
            <small>{index + 2}m ago</small>
          </div>
        ))}
      </div>
    </div>
  )
}

function SeverityPanel() {
  return (
    <div className="vtx-bento-card">
      <div className="vtx-bc-header"><h3>Events by Severity</h3></div>
      <div className="vtx-severity-list">
        {['Critical 38', 'High 454', 'Medium 1,872', 'Low 6,318', 'Info 16,210'].map((item, index) => <div key={item}><span>{index + 1}</span>{item}</div>)}
      </div>
    </div>
  )
}

function SecurityIncidents() {
  return (
    <div className="vtx-bento-card">
      <div className="vtx-bc-header"><h3>Security Incidents</h3><span className="vtx-bc-link">View All</span></div>
      <div className="vtx-incident-card"><AlertTriangle size={26} /><strong>7</strong><span>Incidents last 7 days</span></div>
      <div className="vtx-metric-list"><div>Token grab link <strong>2</strong></div><div>Phishing attempt <strong>2</strong></div><div>Malicious link <strong>2</strong></div><div>IP ban evasion <strong>1</strong></div></div>
    </div>
  )
}

function LogDetails() {
  return (
    <div className="vtx-bento-card">
      <div className="vtx-bc-header"><h3>Log Details</h3><span className="vtx-bc-link">Close</span></div>
      <div className="vtx-log-detail">
        <Trash2 size={18} />
        <strong>Message Deleted</strong>
        <small>ID: 248392847502938475</small>
        <p>Check out this sketchy link http://free-nitro-discord.ml/claim</p>
        <div>Detected by <span>Vortex AutoMod</span></div>
        <div>Actions taken <span>Message deleted, user warned</span></div>
      </div>
    </div>
  )
}

function LogTable() {
  return (
    <div className="vtx-bento-card col-span-4">
      <div className="vtx-log-toolbar"><span><Search size={14} /> Search logs...</span><button><Filter size={14} /> More Filters</button><button><Download size={14} /> Export Logs</button></div>
      <div className="vtx-log-table">
        {timeline.map(([time, label, detail, severity, color]) => (
          <div key={`${time}-table`} style={{ '--row-color': color }}>
            <span>{time}</span><strong>{label}</strong><span>{detail}</span><em>{severity}</em><small># general</small>
          </div>
        ))}
      </div>
    </div>
  )
}

function SystemOverview() {
  return (
    <div className="vtx-bento-card col-span-2">
      <div className="vtx-bc-header"><h3>System Overview</h3><span className="vtx-bc-link">Live</span></div>
      <div className="vtx-system-grid">
        {[
          ['CPU Usage', '23%', 'var(--success)'],
          ['Memory Usage', '41%', 'var(--brand-primary)'],
          ['Disk Usage', '31%', 'var(--info)'],
          ['Network In', '1.2 MB/s', 'var(--success)'],
          ['Network Out', '2.4 MB/s', 'var(--warning)'],
        ].map(([label, value, color]) => <div key={label}><span>{label}</span><strong>{value}</strong><Sparkline color={color} values={[8, 14, 9, 18, 12, 21, 15]} /></div>)}
      </div>
    </div>
  )
}

function ScheduledTasks() {
  return (
    <div className="vtx-bento-card col-span-2">
      <div className="vtx-bc-header"><h3>Next Scheduled Tasks</h3><span className="vtx-bc-link">View All</span></div>
      <div className="vtx-task-list">
        {[[ArchiveRestore, 'Auto Backup', 'Today at 2:00 AM'], [FileText, 'Audit Log Export', 'Today at 5:00 AM'], [Save, 'Data Cleanup', 'Tomorrow at 3:00 AM']].map(([Icon, task, time]) => (
          <div key={task}><Icon size={15} /><span>{task}</span><strong>{time}</strong></div>
        ))}
      </div>
    </div>
  )
}
