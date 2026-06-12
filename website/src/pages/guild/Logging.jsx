import { useState, useEffect, useCallback } from 'react'
import {
  ScrollText, Hash, Shield, MessageSquare, Users, Mic,
  Zap, AlertTriangle, CheckCircle2, XCircle, Save, Loader2
} from 'lucide-react'
import { useGuild } from '../GuildDashboard'
import { api } from '../../api'

const LOG_CHANNELS = [
  { key: 'mod_log_channel', label: 'Moderation Log', icon: Shield, color: '#f87171', desc: 'Bans, kicks, warns, timeouts' },
  { key: 'audit_log_channel', label: 'Audit Log', icon: Users, color: '#7c6df0', desc: 'Member joins, leaves, role changes' },
  { key: 'message_log_channel', label: 'Message Log', icon: MessageSquare, color: '#38bdf8', desc: 'Deleted and edited messages' },
  { key: 'voice_log_channel', label: 'Voice Log', icon: Mic, color: '#34d399', desc: 'Voice joins, leaves, moves' },
  { key: 'automod_log_channel', label: 'AutoMod Log', icon: Zap, color: '#fbbf24', desc: 'Auto-moderation triggers and actions' },
  { key: 'report_log_channel', label: 'Report Log', icon: AlertTriangle, color: '#f97316', desc: 'User reports and escalations' },
]

export default function Logging() {
  const { guildId, config, updateConfig } = useGuild()
  const [channels, setChannels] = useState([])
  const [values, setValues] = useState({})
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getGuildChannels(guildId)
      .then(setChannels)
      .catch(() => setChannels([]))
      .finally(() => setLoading(false))
  }, [guildId])

  useEffect(() => {
    const settings = config?.settings || {}
    const initial = {}
    LOG_CHANNELS.forEach(lc => {
      initial[lc.key] = settings[lc.key] || ''
    })
    setValues(initial)
  }, [config])

  const handleChange = useCallback((key, value) => {
    setValues(prev => ({ ...prev, [key]: value }))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateConfig(values)
      setToast({ message: 'Logging settings saved', type: 'success' })
    } catch {
      setToast({ message: 'Failed to save', type: 'error' })
    }
    setSaving(false)
    setTimeout(() => setToast(null), 2500)
  }

  const textChannels = channels.filter(c => c.type === 0 || c.type === 5)

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Logging</h1>
        <p className="page-subtitle">Route server events to dedicated log channels.</p>
      </div>

      {loading ? (
        <div className="empty-state">
          <Loader2 size={32} className="spin" />
          <p>Loading channels...</p>
        </div>
      ) : (
        <>
          <div className="log-channel-grid">
            {LOG_CHANNELS.map(lc => (
              <div className="log-channel-card" key={lc.key}>
                <div className="log-channel-header">
                  <div
                    className="log-channel-icon"
                    style={{ background: `${lc.color}12`, color: lc.color }}
                  >
                    <lc.icon size={18} />
                  </div>
                  <div>
                    <div className="log-channel-title">{lc.label}</div>
                    <div className="log-channel-desc">{lc.desc}</div>
                  </div>
                </div>
                <select
                  className="select"
                  value={values[lc.key] || ''}
                  onChange={e => handleChange(lc.key, e.target.value)}
                >
                  <option value="">Not configured</option>
                  {textChannels.map(ch => (
                    <option key={ch.id} value={ch.id}>#{ch.name}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 24, display: 'flex', justifyContent: 'flex-end' }}>
            <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? <Loader2 size={16} className="spin" /> : <Save size={16} />}
              Save Logging Settings
            </button>
          </div>
        </>
      )}

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
