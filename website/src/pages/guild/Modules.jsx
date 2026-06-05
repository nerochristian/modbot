import { useState } from 'react'
import {
  Zap, Shield, Brain, ShieldAlert, ScrollText, Ticket,
  ShieldCheck, MessageSquare, Lock, Eye, CheckCircle2,
  XCircle, ChevronRight, Settings
} from 'lucide-react'
import { useGuild } from '../GuildDashboard'

const MODULE_META = [
  {
    id: 'automod',
    name: 'Auto Moderation',
    desc: 'Automatically filter spam, links, invites, and unsafe content with configurable rules.',
    icon: Zap,
    color: '#6C5CE7',
    category: 'Moderation',
    settingKey: 'automod_enabled',
    defaultEnabled: true,
  },
  {
    id: 'aimod',
    name: 'AI Moderation',
    desc: 'Gemini-powered AI assistant that understands context and takes autonomous moderation actions.',
    icon: Brain,
    color: '#00b4d8',
    category: 'Moderation',
    settingKey: 'aimod_enabled',
    defaultEnabled: false,
  },
  {
    id: 'antiraid',
    name: 'Anti-Raid',
    desc: 'Detect mass joins and suspicious accounts with automatic lockdown and quarantine.',
    icon: ShieldAlert,
    color: '#ff4d6a',
    category: 'Protection',
    settingKey: 'antiraid_enabled',
    defaultEnabled: false,
  },
  {
    id: 'logging',
    name: 'Logging',
    desc: 'Rich embeds for every server event — messages, members, roles, voice, and more.',
    icon: ScrollText,
    color: '#ffb800',
    category: 'Utility',
    settingKey: 'logging_enabled',
    defaultEnabled: true,
  },
  {
    id: 'tickets',
    name: 'Tickets',
    desc: 'Full support ticket workflow with categories, transcripts, and staff routing.',
    icon: Ticket,
    color: '#00d68f',
    category: 'Support',
    settingKey: 'tickets_enabled',
    defaultEnabled: false,
  },
  {
    id: 'verification',
    name: 'Verification',
    desc: 'Configurable member verification gate with optional voice verification flow.',
    icon: ShieldCheck,
    color: '#a29bfe',
    category: 'Protection',
    settingKey: 'verification_enabled',
    defaultEnabled: true,
  },
  {
    id: 'modmail',
    name: 'Modmail',
    desc: 'Private DM bridge between users and staff with threaded conversations.',
    icon: MessageSquare,
    color: '#e0c3fc',
    category: 'Support',
    settingKey: 'modmail_enabled',
    defaultEnabled: true,
  },
  {
    id: 'whitelist',
    name: 'Whitelist',
    desc: 'Restrict server access to approved users only with automatic kick on join.',
    icon: Lock,
    color: '#f97316',
    category: 'Protection',
    settingKey: 'whitelist_enabled',
    defaultEnabled: false,
  },
  {
    id: 'forum_moderation',
    name: 'Forum Moderation',
    desc: 'Moderate forum posts and route flagged content to alerts channel.',
    icon: Eye,
    color: '#06d6a0',
    category: 'Moderation',
    settingKey: 'forum_moderation_enabled',
    defaultEnabled: true,
  },
]

export default function Modules() {
  const { config, updateConfig } = useGuild()
  const [togglingId, setTogglingId] = useState(null)
  const [toast, setToast] = useState(null)

  const settings = config?.settings || {}

  const isEnabled = (mod) => {
    const val = settings[mod.settingKey]
    if (val === undefined || val === null) return mod.defaultEnabled
    if (typeof val === 'boolean') return val
    if (typeof val === 'string') return val.toLowerCase() !== 'false' && val !== '0'
    return Boolean(val)
  }

  const handleToggle = async (mod) => {
    const current = isEnabled(mod)
    setTogglingId(mod.id)
    try {
      await updateConfig({ [mod.settingKey]: !current })
      showToast(`${mod.name} ${!current ? 'enabled' : 'disabled'}`, !current ? 'success' : 'error')
    } catch {
      showToast('Failed to update', 'error')
    }
    setTogglingId(null)
  }

  const showToast = (message, type) => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  const categories = [...new Set(MODULE_META.map(m => m.category))]

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Modules</h1>
        <p className="page-subtitle">Enable or disable bot features for your server.</p>
      </div>

      {categories.map(cat => (
        <div className="page-section" key={cat}>
          <h2 className="page-section-title">
            <Shield size={16} />
            {cat}
          </h2>
          <div className="page-grid">
            {MODULE_META.filter(m => m.category === cat).map(mod => {
              const enabled = isEnabled(mod)
              const toggling = togglingId === mod.id
              return (
                <div className="module-card" key={mod.id}>
                  <div className="module-card-header">
                    <div className="module-card-left">
                      <div
                        className="module-card-icon"
                        style={{ background: `${mod.color}18`, color: mod.color }}
                      >
                        <mod.icon size={20} />
                      </div>
                      <div>
                        <div className="module-card-title">{mod.name}</div>
                        <div className="module-card-cat">{mod.category}</div>
                      </div>
                    </div>
                  </div>
                  <p className="module-card-desc">{mod.desc}</p>
                  <div className="module-card-footer">
                    <span className={`badge ${enabled ? 'badge-success' : 'badge-error'}`}>
                      {enabled ? 'Enabled' : 'Disabled'}
                    </span>
                    <button
                      className={`toggle ${enabled ? 'active' : ''}`}
                      onClick={() => handleToggle(mod)}
                      disabled={toggling}
                      title={enabled ? 'Disable' : 'Enable'}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ))}

      {/* Toast */}
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
