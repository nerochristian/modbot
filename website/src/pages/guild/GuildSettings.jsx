import { useState, useEffect } from 'react'
import {
  Settings, Hash, CheckCircle2, XCircle, Save,
  RefreshCw, AlertTriangle, Shield, Loader2
} from 'lucide-react'
import { useGuild } from '../GuildDashboard'
import { api } from '../../api'

export default function GuildSettings() {
  const { config, guildId, updateConfig } = useGuild()
  const [toast, setToast] = useState(null)
  const [saving, setSaving] = useState(false)
  const [channels, setChannels] = useState([])
  const [roles, setRoles] = useState([])
  const [form, setForm] = useState({})

  const settings = config?.settings || {}

  useEffect(() => {
    setForm({
      prefix: settings.prefix || ',',
      mod_role: settings.mod_role || '',
      admin_role: settings.admin_role || '',
      mute_role: settings.mute_role || '',
      staff_role: settings.staff_role || '',
      welcome_channel: settings.welcome_channel || '',
      welcome_message: settings.welcome_message || '',
    })
  }, [config])

  useEffect(() => {
    Promise.all([
      api.getGuildChannels(guildId).catch(() => []),
      api.getGuildRoles(guildId).catch(() => []),
    ]).then(([ch, r]) => {
      setChannels(ch.filter(c => c.type === 0))
      setRoles(r.filter(r => !r.managed && r.name !== '@everyone'))
    })
  }, [guildId])

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateConfig(form)
      showToast('Settings saved successfully', 'success')
    } catch {
      showToast('Failed to save settings', 'error')
    }
    setSaving(false)
  }

  const handleSync = async () => {
    setSaving(true)
    try {
      await api.syncCommands(guildId)
      showToast('Commands synced successfully', 'success')
    } catch {
      showToast('Failed to sync commands', 'error')
    }
    setSaving(false)
  }

  const showToast = (message, type) => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  const updateField = (key, value) => {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Server Settings</h1>
        <p className="page-subtitle">Configure Orion Protection's core behavior for this server.</p>
      </div>

      {/* General */}
      <div className="settings-group">
        <div className="settings-group-title">
          <Settings size={18} />
          General
        </div>
        <div className="settings-row">
          <div className="settings-label">
            <span>Command Prefix</span>
            <span>The prefix used for text commands</span>
          </div>
          <input
            className="input"
            style={{ maxWidth: 120 }}
            value={form.prefix || ''}
            onChange={e => updateField('prefix', e.target.value)}
            maxLength={5}
          />
        </div>
      </div>

      {/* Roles */}
      <div className="settings-group">
        <div className="settings-group-title">
          <Shield size={18} />
          Staff Roles
        </div>

        {[
          { key: 'admin_role', label: 'Admin Role', desc: 'Full bot management access' },
          { key: 'mod_role', label: 'Moderator Role', desc: 'Moderation commands access' },
          { key: 'staff_role', label: 'Staff Role', desc: 'Basic staff permissions' },
          { key: 'mute_role', label: 'Mute Role', desc: 'Role applied when muting users' },
        ].map(item => (
          <div className="settings-row" key={item.key}>
            <div className="settings-label">
              <span>{item.label}</span>
              <span>{item.desc}</span>
            </div>
            <select
              className="input"
              style={{ maxWidth: 240 }}
              value={form[item.key] || ''}
              onChange={e => updateField(item.key, e.target.value)}
            >
              <option value="">Not set</option>
              {roles.map(r => (
                <option key={r.id} value={r.id}>@{r.name}</option>
              ))}
            </select>
          </div>
        ))}
      </div>

      {/* Welcome */}
      <div className="settings-group">
        <div className="settings-group-title">
          <Hash size={18} />
          Welcome System
        </div>
        <div className="settings-row">
          <div className="settings-label">
            <span>Welcome Channel</span>
            <span>Channel to send welcome messages in</span>
          </div>
          <select
            className="input"
            style={{ maxWidth: 240 }}
            value={form.welcome_channel || ''}
            onChange={e => updateField('welcome_channel', e.target.value)}
          >
            <option value="">Not set</option>
            {channels.map(c => (
              <option key={c.id} value={c.id}>#{c.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Actions */}
      <div className="settings-actions">
        <button
          className="btn btn-primary"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? <Loader2 size={16} className="spin" /> : <Save size={16} />}
          Save Settings
        </button>
        <button
          className="btn btn-secondary"
          onClick={handleSync}
          disabled={saving}
        >
          <RefreshCw size={16} />
          Sync Commands
        </button>
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
