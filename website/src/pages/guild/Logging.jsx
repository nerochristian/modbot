import { useState, useEffect } from 'react'
import {
  ScrollText, Hash, CheckCircle2, XCircle, AlertCircle,
  MessageSquare, Users, Gavel, Zap, Mic, Shield
} from 'lucide-react'
import { useGuild } from '../GuildDashboard'
import { api } from '../../api'

const LOG_CHANNELS = [
  { key: 'mod_log_channel', label: 'Moderation Logs', icon: Gavel, desc: 'Ban, kick, warn, mute actions' },
  { key: 'audit_log_channel', label: 'Audit Logs', icon: Shield, desc: 'Member joins/leaves, role changes' },
  { key: 'message_log_channel', label: 'Message Logs', icon: MessageSquare, desc: 'Deleted & edited messages' },
  { key: 'voice_log_channel', label: 'Voice Logs', icon: Mic, desc: 'Voice joins, leaves, and moves' },
  { key: 'automod_log_channel', label: 'AutoMod Logs', icon: Zap, desc: 'Auto-moderation triggers' },
  { key: 'report_log_channel', label: 'Report Logs', icon: AlertCircle, desc: 'User report submissions' },
  { key: 'ticket_log_channel', label: 'Ticket Logs', icon: ScrollText, desc: 'Ticket open/close/transcripts' },
]

export default function Logging() {
  const { config, guildId, updateConfig } = useGuild()
  const [channels, setChannels] = useState([])
  const [toast, setToast] = useState(null)
  const [saving, setSaving] = useState(null)

  const settings = config?.settings || {}

  useEffect(() => {
    api.getGuildChannels(guildId)
      .then(data => setChannels(data.filter(c => c.type === 0)))
      .catch(() => {})
  }, [guildId])

  const handleChange = async (key, value) => {
    setSaving(key)
    try {
      await updateConfig({ [key]: value || null })
      showToast('Log channel updated', 'success')
    } catch {
      showToast('Failed to update', 'error')
    }
    setSaving(null)
  }

  const showToast = (message, type) => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Logging</h1>
        <p className="page-subtitle">Route server events to dedicated log channels.</p>
      </div>

      <div className="settings-group">
        <div className="settings-group-title">
          <ScrollText size={18} />
          Log Channels
        </div>
        {LOG_CHANNELS.map(lc => {
          const currentValue = settings[lc.key] || ''
          return (
            <div className="settings-row" key={lc.key}>
              <div className="settings-label">
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <lc.icon size={16} style={{ color: 'var(--brand-secondary)', flexShrink: 0 }} />
                  {lc.label}
                </span>
                <span>{lc.desc}</span>
              </div>
              <div className="settings-input">
                <select
                  className="input"
                  value={currentValue}
                  onChange={e => handleChange(lc.key, e.target.value)}
                  disabled={saving === lc.key}
                  style={{ minWidth: 200 }}
                >
                  <option value="">Not set</option>
                  {channels.map(ch => (
                    <option key={ch.id} value={ch.id}>
                      #{ch.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )
        })}
      </div>

      {/* Status */}
      <div className="page-section">
        <h2 className="page-section-title">
          <CheckCircle2 size={16} />
          Channel Status
        </h2>
        <div className="page-grid">
          {LOG_CHANNELS.map(lc => {
            const configured = Boolean(settings[lc.key])
            const channel = channels.find(c => c.id === settings[lc.key])
            return (
              <div
                className="activity-item"
                key={lc.key}
                style={{ borderColor: configured ? 'rgba(0,214,143,0.15)' : 'rgba(255,77,106,0.08)' }}
              >
                <div
                  className="activity-dot"
                  style={{ background: configured ? 'var(--success)' : 'var(--error)' }}
                />
                <span className="activity-text">
                  {lc.label}
                  {configured && channel && (
                    <span style={{ color: 'var(--text-muted)', marginLeft: 4 }}>
                      → #{channel.name}
                    </span>
                  )}
                </span>
                <span className={`badge ${configured ? 'badge-success' : 'badge-error'}`}
                  style={{ fontSize: '0.65rem' }}>
                  {configured ? 'Set' : 'Not set'}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {toast && (
        <div className="toast-container">
          <div className={`toast toast-${toast.type}`}>
            {toast.type === 'success' ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
            {toast.message}
          </div>
        </div>
      )}
    </div>
  )
}
