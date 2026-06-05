import { useState, useEffect } from 'react'
import {
  Users, Shield, Gavel, MessageSquare, Zap, BarChart3,
  TrendingUp, Activity, Clock, ShieldCheck, AlertTriangle,
  Bot, Hash, Mic, Eye
} from 'lucide-react'
import { useGuild } from '../GuildDashboard'
import { api } from '../../api'

export default function Overview() {
  const { guild, config, guildId } = useGuild()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getGuildStats(guildId)
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [guildId])

  const settings = config?.settings || {}
  const modules = config?.modules || {}

  // Count enabled modules
  const enabledModules = Object.values(modules).filter(m =>
    m && (m.enabled === true || m.enabled === undefined)
  ).length

  const statCards = [
    {
      icon: Users,
      label: 'Members',
      value: guild?.memberCount?.toLocaleString() || '0',
      color: '#6C5CE7',
      bg: 'rgba(108,92,231,0.12)',
    },
    {
      icon: Zap,
      label: 'Modules',
      value: enabledModules || Object.keys(modules).length || '—',
      color: '#00b4d8',
      bg: 'rgba(0,180,216,0.12)',
    },
    {
      icon: Gavel,
      label: 'Cases Today',
      value: stats?.casesToday?.toLocaleString() || '0',
      color: '#ffb800',
      bg: 'rgba(255,184,0,0.12)',
    },
    {
      icon: MessageSquare,
      label: 'Messages Today',
      value: stats?.messagesToday?.toLocaleString() || '0',
      color: '#00d68f',
      bg: 'rgba(0,214,143,0.12)',
    },
  ]

  const recentActivity = [
    { color: 'var(--success)', text: 'Auto Mod is actively monitoring', time: 'Live' },
    { color: 'var(--brand-primary)', text: `Prefix set to "${settings.prefix || ','}"`, time: 'Config' },
    { color: 'var(--info)', text: `${enabledModules || 0} modules active`, time: 'Status' },
  ]

  // Quick module status
  const moduleStatus = [
    { name: 'Auto Moderation', key: 'automod', icon: Zap, settingKey: 'automod_enabled' },
    { name: 'AI Moderation', key: 'aimod', icon: Bot, settingKey: 'aimod_enabled' },
    { name: 'Anti-Raid', key: 'antiraid', icon: ShieldCheck, settingKey: 'antiraid_enabled' },
    { name: 'Logging', key: 'logging', icon: Eye, settingKey: 'logging_enabled' },
    { name: 'Tickets', key: 'tickets', icon: MessageSquare, settingKey: 'tickets_enabled' },
    { name: 'Verification', key: 'verification', icon: Shield, settingKey: 'verification_enabled' },
  ]

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Server Overview</h1>
        <p className="page-subtitle">
          Monitor and manage {guild?.name || 'your server'} at a glance.
        </p>
      </div>

      {/* Stat Cards */}
      <div className="stat-card-grid">
        {statCards.map((s, i) => (
          <div className="stat-card-item" key={i}>
            <div className="stat-icon" style={{ background: s.bg, color: s.color }}>
              <s.icon size={22} />
            </div>
            <div className="stat-info">
              <span className="stat-number">{loading ? '...' : s.value}</span>
              <span className="stat-name">{s.label}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Module Status */}
      <div className="page-section">
        <h2 className="page-section-title">
          <Activity size={18} />
          Module Status
        </h2>
        <div className="page-grid">
          {moduleStatus.map((mod, i) => {
            const isEnabled = settings[mod.settingKey] !== false &&
              settings[mod.settingKey] !== 'false' &&
              settings[mod.settingKey] !== 0
            return (
              <div className="module-status-card" key={i}>
                <div className="module-status-left">
                  <div
                    className="module-status-icon"
                    style={{
                      background: isEnabled ? 'rgba(0,214,143,0.1)' : 'rgba(255,77,106,0.1)',
                      color: isEnabled ? 'var(--success)' : 'var(--error)',
                    }}
                  >
                    <mod.icon size={18} />
                  </div>
                  <span className="module-status-name">{mod.name}</span>
                </div>
                <span className={`badge ${isEnabled ? 'badge-success' : 'badge-error'}`}>
                  {isEnabled ? 'Active' : 'Disabled'}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Activity */}
      <div className="page-section">
        <h2 className="page-section-title">
          <Clock size={18} />
          Quick Info
        </h2>
        <div className="activity-feed">
          {recentActivity.map((a, i) => (
            <div className="activity-item" key={i}>
              <div className="activity-dot" style={{ background: a.color }} />
              <span className="activity-text">{a.text}</span>
              <span className="activity-time">{a.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
