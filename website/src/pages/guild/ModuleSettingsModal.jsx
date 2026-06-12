import { useState } from 'react'
import {
  X, Settings, Shield, Hash, Zap, ScrollText, Image, Clock,
  Users, Bell, Link, SlidersHorizontal, CheckCircle2, XCircle, Save, Loader2
} from 'lucide-react'

const SETTINGS_TABS = [
  { id: 'general', label: 'General', icon: Settings },
  { id: 'permissions', label: 'Permissions', icon: Shield },
  { id: 'channels', label: 'Channels', icon: Hash },
  { id: 'triggers', label: 'Triggers', icon: Zap },
  { id: 'logs', label: 'Logs', icon: ScrollText },
  { id: 'embeds', label: 'Embeds', icon: Image },
  { id: 'ratelimits', label: 'Rate Limits', icon: Clock },
  { id: 'roles', label: 'Role Rules', icon: Users },
  { id: 'schedule', label: 'Schedule', icon: Bell },
  { id: 'webhooks', label: 'Webhooks', icon: Link },
  { id: 'advanced', label: 'Advanced', icon: SlidersHorizontal },
]

export default function ModuleSettingsModal({ module, onClose }) {
  const [activeTab, setActiveTab] = useState('general')
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState(null)

  const handleSave = async () => {
    setSaving(true)
    await new Promise(r => setTimeout(r, 600))
    setSaving(false)
    setToast({ message: 'Settings saved', type: 'success' })
    setTimeout(() => setToast(null), 2000)
  }

  return (
    <div className="msm-overlay" onClick={onClose}>
      <div className="msm" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="msm-header">
          <div className="msm-header-left">
            <div className="msm-icon" style={{ background: `${module.color}15`, color: module.color }}>
              <module.icon size={20} />
            </div>
            <div>
              <h2 className="msm-title">{module.name} Settings</h2>
              <p className="msm-subtitle">{module.category} Module</p>
            </div>
          </div>
          <button className="msm-close" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="msm-body">
          {/* Tabs sidebar */}
          <div className="msm-tabs">
            {SETTINGS_TABS.map(tab => (
              <button
                key={tab.id}
                className={`msm-tab ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <tab.icon size={15} />
                {tab.label}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="msm-content">
            {activeTab === 'general' && (
              <div className="msm-section">
                <h3 className="msm-section-title">General Settings</h3>
                <div className="msm-field">
                  <label>Module Name Override</label>
                  <input type="text" className="input" placeholder={module.name} />
                </div>
                <div className="msm-field">
                  <label>Response Style</label>
                  <select className="input">
                    <option>Embed</option>
                    <option>Plain Text</option>
                    <option>Ephemeral</option>
                  </select>
                </div>
                <div className="msm-field-row">
                  <div className="msm-field-info">
                    <span>Delete Trigger Messages</span>
                    <span className="msm-field-hint">Automatically delete the command message</span>
                  </div>
                  <button className="mp-toggle on"><span className="mp-toggle-thumb" /></button>
                </div>
                <div className="msm-field-row">
                  <div className="msm-field-info">
                    <span>Silent Mode</span>
                    <span className="msm-field-hint">Suppress all module notifications</span>
                  </div>
                  <button className="mp-toggle"><span className="mp-toggle-thumb" /></button>
                </div>
              </div>
            )}

            {activeTab === 'permissions' && (
              <div className="msm-section">
                <h3 className="msm-section-title">Permission Rules</h3>
                <div className="msm-field">
                  <label>Required Permission</label>
                  <select className="input">
                    <option>Send Messages</option>
                    <option>Manage Messages</option>
                    <option>Manage Server</option>
                    <option>Administrator</option>
                  </select>
                </div>
                <div className="msm-field">
                  <label>Minimum Staff Level</label>
                  <select className="input">
                    <option>Everyone</option>
                    <option>Moderator</option>
                    <option>Admin</option>
                    <option>Owner</option>
                  </select>
                </div>
                <div className="msm-field-row">
                  <div className="msm-field-info">
                    <span>Enforce Role Hierarchy</span>
                    <span className="msm-field-hint">Prevent targeting users above your role</span>
                  </div>
                  <button className="mp-toggle on"><span className="mp-toggle-thumb" /></button>
                </div>
              </div>
            )}

            {activeTab === 'channels' && (
              <div className="msm-section">
                <h3 className="msm-section-title">Channel Configuration</h3>
                <div className="msm-field">
                  <label>Channel Mode</label>
                  <select className="input">
                    <option>Enabled Everywhere</option>
                    <option>Whitelist Only</option>
                    <option>Blacklist Channels</option>
                  </select>
                </div>
                <div className="msm-field">
                  <label>Allowed Channels</label>
                  <input type="text" className="input" placeholder="Search and add channels..." />
                </div>
                <div className="msm-field-row">
                  <div className="msm-field-info">
                    <span>Disable in Threads</span>
                    <span className="msm-field-hint">Prevent module from running in threads</span>
                  </div>
                  <button className="mp-toggle"><span className="mp-toggle-thumb" /></button>
                </div>
              </div>
            )}

            {activeTab === 'ratelimits' && (
              <div className="msm-section">
                <h3 className="msm-section-title">Rate Limits & Cooldowns</h3>
                <div className="msm-field">
                  <label>Per-User Cooldown (seconds)</label>
                  <input type="number" className="input" defaultValue={5} min={0} max={3600} />
                </div>
                <div className="msm-field">
                  <label>Per-Channel Cooldown (seconds)</label>
                  <input type="number" className="input" defaultValue={0} min={0} max={3600} />
                </div>
                <div className="msm-field">
                  <label>Max Uses Per Minute</label>
                  <input type="number" className="input" defaultValue={30} min={0} max={300} />
                </div>
              </div>
            )}

            {!['general', 'permissions', 'channels', 'ratelimits'].includes(activeTab) && (
              <div className="msm-section">
                <h3 className="msm-section-title">{SETTINGS_TABS.find(t => t.id === activeTab)?.label}</h3>
                <div className="msm-empty">
                  <SlidersHorizontal size={32} />
                  <p>Configure {SETTINGS_TABS.find(t => t.id === activeTab)?.label.toLowerCase()} settings for {module.name}.</p>
                  <span className="msm-empty-hint">Settings will appear here once configured.</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="msm-footer">
          <button className="btn btn-ghost btn-sm" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 size={14} className="spin" /> : <Save size={14} />}
            Save Changes
          </button>
        </div>

        {toast && (
          <div className="toast-container" style={{ position: 'absolute' }}>
            <div className={`toast toast-${toast.type}`}>
              <CheckCircle2 size={16} />{toast.message}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
