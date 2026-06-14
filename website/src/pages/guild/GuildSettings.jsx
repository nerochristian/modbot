import { useState, useEffect, useCallback } from 'react'
import {
  Settings, Shield, Hash, Users, Terminal, Save, Loader2,
  CheckCircle2, XCircle, AlertTriangle, Trash2, RefreshCw
} from 'lucide-react'
import { useGuild } from './GuildContext'
import { api } from '../../api'

export default function GuildSettings() {
  const { guild, guildId, config, updateConfig } = useGuild()
  const [channels, setChannels] = useState([])
  const [roles, setRoles] = useState([])
  const [values, setValues] = useState({})
  const [saving, setSaving] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [toast, setToast] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.getGuildChannels(guildId).catch(() => []),
      api.getGuildRoles(guildId).catch(() => []),
    ]).then(([ch, ro]) => {
      setChannels(ch)
      setRoles(ro)
    }).finally(() => setLoading(false))
  }, [guildId])

  useEffect(() => {
    const s = config?.settings || {}
    setValues({
      prefix: s.prefix || ',',
      staff_role: s.staff_role || '',
      admin_role: s.admin_role || '',
      mute_role: s.mute_role || '',
      log_channel: s.log_channel || '',
      mod_log_channel: s.mod_log_channel || '',
      disabled_channels: s.disabled_channels || '',
      embed_color: s.embed_color || '#d4952a',
    })
  }, [config])

  const showToast = useCallback((msg, type = 'success') => {
    setToast({ message: msg, type })
    setTimeout(() => setToast(null), 3000)
  }, [])

  const handleChange = useCallback((key, value) => {
    setValues(prev => ({ ...prev, [key]: value }))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateConfig(values)
      showToast('Settings saved successfully')
    } catch {
      showToast('Failed to save settings', 'error')
    }
    setSaving(false)
  }

  const handleSync = async () => {
    setSyncing(true)
    try {
      await api.syncCommands(guildId)
      showToast('Commands synced successfully')
    } catch {
      showToast('Failed to sync commands', 'error')
    }
    setSyncing(false)
  }

  const textChannels = channels.filter(c => c.type === 0 || c.type === 5)

  if (loading) {
    return (
      <div className="empty-state">
        <Loader2 size={32} className="spin" />
        <p>Loading settings...</p>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Server Settings</h1>
        <p className="page-subtitle">Configure core bot settings for {guild?.name || 'this server'}.</p>
      </div>

      {/* General */}
      <div className="settings-section">
        <div className="settings-section-title">
          <Settings size={16} />
          General
        </div>
        <div className="settings-grid">
          <div className="settings-card">
            <label className="settings-card-label">Command Prefix</label>
            <div className="settings-card-desc">The prefix used for text commands.</div>
            <input
              type="text"
              className="input"
              value={values.prefix}
              onChange={e => handleChange('prefix', e.target.value)}
              maxLength={5}
            />
          </div>
          <div className="settings-card">
            <label className="settings-card-label">Embed Color</label>
            <div className="settings-card-desc">Default color for bot embeds.</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <input
                type="color"
                value={values.embed_color}
                onChange={e => handleChange('embed_color', e.target.value)}
                style={{ 
                  width: 40, height: 34, 
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                  background: 'transparent',
                  padding: 2,
                }}
              />
              <input
                type="text"
                className="input"
                value={values.embed_color}
                onChange={e => handleChange('embed_color', e.target.value)}
                style={{ flex: 1 }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Roles */}
      <div className="settings-section">
        <div className="settings-section-title">
          <Users size={16} />
          Staff Roles
        </div>
        <div className="settings-grid">
          <div className="settings-card">
            <label className="settings-card-label">Moderator Role</label>
            <div className="settings-card-desc">Members with this role can use moderation commands.</div>
            <select
              className="select"
              value={values.staff_role}
              onChange={e => handleChange('staff_role', e.target.value)}
            >
              <option value="">None</option>
              {roles.map(r => (
                <option key={r.id} value={r.id}>@{r.name}</option>
              ))}
            </select>
          </div>
          <div className="settings-card">
            <label className="settings-card-label">Admin Role</label>
            <div className="settings-card-desc">Members with this role have full bot access.</div>
            <select
              className="select"
              value={values.admin_role}
              onChange={e => handleChange('admin_role', e.target.value)}
            >
              <option value="">None</option>
              {roles.map(r => (
                <option key={r.id} value={r.id}>@{r.name}</option>
              ))}
            </select>
          </div>
          <div className="settings-card">
            <label className="settings-card-label">Mute Role</label>
            <div className="settings-card-desc">Role assigned when a member is muted.</div>
            <select
              className="select"
              value={values.mute_role}
              onChange={e => handleChange('mute_role', e.target.value)}
            >
              <option value="">None (use Discord timeout)</option>
              {roles.map(r => (
                <option key={r.id} value={r.id}>@{r.name}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Save */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 24, marginBottom: 24 }}>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? <Loader2 size={16} className="spin" /> : <Save size={16} />}
          Save Settings
        </button>
      </div>

      {/* Danger Zone */}
      <div className="danger-zone">
        <div className="danger-zone-title">
          <AlertTriangle size={18} />
          Advanced Actions
        </div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <button className="btn btn-secondary btn-sm" onClick={handleSync} disabled={syncing}>
            {syncing ? <Loader2 size={14} className="spin" /> : <RefreshCw size={14} />}
            Sync Slash Commands
          </button>
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
