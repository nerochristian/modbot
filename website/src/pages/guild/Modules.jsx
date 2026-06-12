import { useState, useMemo, useCallback, useEffect } from 'react'
import {
  Search, Settings, X, Zap, Shield, ShieldAlert, ScrollText,
  Ticket, MessageSquare, Lock, Eye, Users, Crown, Sparkles,
  BarChart3, Clock, Bell, Terminal, CheckCircle2, XCircle,
  ArrowUpDown, Loader2, Package, Bot, UserCheck, Mail, Filter
} from 'lucide-react'
import { useGuild } from './GuildContext'
import { api } from '../../api'
import ModuleSettingsModal from './ModuleSettingsModal'

/* Icon map for dynamic module rendering */
const ICON_MAP = {
  Zap, Shield, ShieldAlert, ScrollText, Ticket, MessageSquare,
  Lock, Eye, Users, Crown, Sparkles, BarChart3, Clock, Bell,
  Terminal, Bot, UserCheck, Mail, Filter,
}

const FALLBACK_MODULES = [
  { id: 'automod', name: 'Auto Moderation', description: 'Automatically filter spam, links, invites, and unsafe content.', category: 'Moderation', iconHint: 'Zap', color: '#6366f1' },
  { id: 'aimod', name: 'AI Moderation', description: 'Mention router with configurable tools, confirmations, and model behavior.', category: 'Moderation', iconHint: 'Shield', color: '#7c6df0' },
  { id: 'antiraid', name: 'Anti-Raid', description: 'Detect mass joins and apply automatic raid responses.', category: 'Protection', iconHint: 'ShieldAlert', color: '#f87171' },
  { id: 'logging', name: 'Logging', description: 'Route moderation and server events to dedicated log channels.', category: 'Utility', iconHint: 'ScrollText', color: '#38bdf8' },
  { id: 'tickets', name: 'Tickets', description: 'Ticket panel, close flow, logs, and support role routing.', category: 'Support', iconHint: 'Ticket', color: '#34d399' },
  { id: 'verification', name: 'Verification', description: 'Configure verification roles and optional voice verification flow.', category: 'Protection', iconHint: 'UserCheck', color: '#fbbf24' },
  { id: 'modmail', name: 'Modmail', description: 'Ticket-style DM bridge between users and staff.', category: 'Support', iconHint: 'Mail', color: '#a78bfa' },
  { id: 'whitelist', name: 'Whitelist', description: 'Allowlist-only server access with join protections.', category: 'Protection', iconHint: 'Lock', color: '#f97316' },
  { id: 'forum_moderation', name: 'Forum Moderation', description: 'Moderate forum posts and route flagged content alerts.', category: 'Moderation', iconHint: 'ShieldAlert', color: '#fb923c' },
]

const ENABLED_KEYS = {
  automod: 'automod_enabled',
  aimod: 'aimod_enabled',
  antiraid: 'antiraid_enabled',
  logging: 'logging_enabled',
  tickets: 'tickets_enabled',
  verification: 'verification_enabled',
  modmail: 'modmail_enabled',
  whitelist: 'whitelist_enabled',
  forum_moderation: 'forum_moderation_enabled',
}

const ENABLED_DEFAULTS = {
  automod: true,
  logging: true,
  verification: true,
  modmail: true,
}

const CATEGORIES = ['All', 'Moderation', 'Protection', 'Support', 'Utility']
const FILTERS = ['All', 'Enabled', 'Disabled']

export default function Modules() {
  const { config, updateConfig, guildId } = useGuild()
  const [capabilities, setCapabilities] = useState(null)
  const [search, setSearch] = useState('')
  const [activeCategory, setActiveCategory] = useState('All')
  const [activeFilter, setActiveFilter] = useState('All')
  const [sortBy, setSortBy] = useState('name')
  const [settingsModule, setSettingsModule] = useState(null)
  const [togglingId, setTogglingId] = useState(null)
  const [toast, setToast] = useState(null)

  // Fetch bot capabilities for module schemas
  useEffect(() => {
    api.request('/api/bot/capabilities')
      .then(setCapabilities)
      .catch(() => setCapabilities({}))
  }, [])

  const settings = config?.settings || {}

  const showToast = useCallback((message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }, [])

  // Build module list from capabilities + fallbacks
  const modules = useMemo(() => {
    const caps = capabilities || {}
    const moduleList = []
    const seen = new Set()

    // From capabilities
    for (const [id, cap] of Object.entries(caps)) {
      seen.add(id)
      const icon = ICON_MAP[cap.iconHint] || Zap
      const enabledKey = ENABLED_KEYS[id]
      const defaultEnabled = ENABLED_DEFAULTS[id] ?? false
      const isEnabled = enabledKey
        ? (settings[enabledKey] !== false && settings[enabledKey] !== 'false' && settings[enabledKey] !== 0 && (settings[enabledKey] !== undefined || defaultEnabled))
        : defaultEnabled

      moduleList.push({
        id,
        name: cap.name || id,
        description: cap.description || '',
        category: cap.category || 'Other',
        icon,
        iconHint: cap.iconHint,
        color: FALLBACK_MODULES.find(f => f.id === id)?.color || '#7c6df0',
        enabled: isEnabled,
        hasSettings: (cap.settingsSchema || []).length > 0,
        settingsSchema: cap.settingsSchema || [],
        supportsOverrides: cap.supportsOverrides || false,
      })
    }

    // Add fallbacks not in capabilities
    for (const fb of FALLBACK_MODULES) {
      if (seen.has(fb.id)) continue
      const enabledKey = ENABLED_KEYS[fb.id]
      const defaultEnabled = ENABLED_DEFAULTS[fb.id] ?? false
      const isEnabled = enabledKey
        ? (settings[enabledKey] !== false && settings[enabledKey] !== 'false' && settings[enabledKey] !== 0 && (settings[enabledKey] !== undefined || defaultEnabled))
        : defaultEnabled

      moduleList.push({
        ...fb,
        icon: ICON_MAP[fb.iconHint] || Zap,
        enabled: isEnabled,
        hasSettings: false,
        settingsSchema: [],
        supportsOverrides: false,
      })
    }

    return moduleList
  }, [capabilities, settings])

  const handleToggle = useCallback(async (mod) => {
    const enabledKey = ENABLED_KEYS[mod.id]
    if (!enabledKey) return

    setTogglingId(mod.id)
    const newEnabled = !mod.enabled
    try {
      await updateConfig({ [enabledKey]: newEnabled })
      showToast(`${mod.name} ${newEnabled ? 'enabled' : 'disabled'}`)
    } catch {
      showToast('Failed to update module', 'error')
    }
    setTogglingId(null)
  }, [updateConfig, showToast])

  const filtered = useMemo(() => {
    let result = [...modules]
    if (search) {
      const q = search.toLowerCase()
      result = result.filter(m => m.name.toLowerCase().includes(q) || m.description.toLowerCase().includes(q))
    }
    if (activeCategory !== 'All') result = result.filter(m => m.category === activeCategory)
    if (activeFilter === 'Enabled') result = result.filter(m => m.enabled)
    else if (activeFilter === 'Disabled') result = result.filter(m => !m.enabled)

    result.sort((a, b) => {
      if (sortBy === 'status') return (b.enabled ? 1 : 0) - (a.enabled ? 1 : 0)
      return a.name.localeCompare(b.name)
    })
    return result
  }, [modules, search, activeCategory, activeFilter, sortBy])

  const counts = useMemo(() => ({
    total: modules.length,
    enabled: modules.filter(m => m.enabled).length,
  }), [modules])

  return (
    <div className="mp">
      {/* Header */}
      <div className="mp-header">
        <div>
          <h1 className="page-title">Modules</h1>
          <p className="page-subtitle">Enable, disable, and configure bot modules for your server.</p>
        </div>
        <div className="mp-counters">
          <div className="mp-counter"><span className="mp-counter-val">{counts.total}</span><span className="mp-counter-lbl">Total</span></div>
          <div className="mp-counter"><span className="mp-counter-val mp-c-green">{counts.enabled}</span><span className="mp-counter-lbl">Enabled</span></div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="mp-toolbar">
        <div className="mp-search">
          <Search size={16} />
          <input type="text" placeholder="Search modules..." value={search} onChange={e => setSearch(e.target.value)} />
          {search && <button className="mp-search-clear" onClick={() => setSearch('')}><X size={14} /></button>}
        </div>
        <div className="mp-sort">
          <ArrowUpDown size={14} />
          <select value={sortBy} onChange={e => setSortBy(e.target.value)}>
            <option value="name">Name</option>
            <option value="status">Status</option>
          </select>
        </div>
      </div>

      {/* Filters */}
      <div className="mp-filters">
        <div className="mp-chip-group">
          {CATEGORIES.map(c => (
            <button key={c} className={`mp-chip ${activeCategory === c ? 'active' : ''}`} onClick={() => setActiveCategory(c)}>{c}</button>
          ))}
        </div>
        <div className="mp-chip-divider" />
        <div className="mp-chip-group">
          {FILTERS.map(f => (
            <button key={f} className={`mp-chip ${activeFilter === f ? 'active' : ''}`} onClick={() => setActiveFilter(f)}>{f}</button>
          ))}
        </div>
      </div>

      {/* Grid */}
      {filtered.length === 0 ? (
        <div className="empty-state">
          <Package size={48} />
          <h3>No modules found</h3>
          <p>Try adjusting your search or filters.</p>
        </div>
      ) : (
        <div className="mp-grid">
          {filtered.map(mod => (
            <div className={`mp-card ${mod.enabled ? 'mp-card-on' : 'mp-card-off'}`} key={mod.id}>
              <div className="mp-card-top">
                <div className="mp-card-icon" style={{ background: `${mod.color}12`, color: mod.color }}>
                  <mod.icon size={20} />
                </div>
                <div className="mp-card-info">
                  <div className="mp-card-name">{mod.name}</div>
                  <div className="mp-card-cat">{mod.category}</div>
                </div>
                <button
                  className={`mp-toggle ${mod.enabled ? 'on' : ''}`}
                  onClick={() => handleToggle(mod)}
                  disabled={togglingId === mod.id || !ENABLED_KEYS[mod.id]}
                  aria-label={mod.enabled ? `Disable ${mod.name}` : `Enable ${mod.name}`}
                >
                  <span className="mp-toggle-thumb" />
                </button>
              </div>
              <p className="mp-card-desc">{mod.description}</p>
              <div className="mp-card-bottom">
                <span className={`mp-status ${mod.enabled ? 'mp-status-on' : 'mp-status-off'}`}>
                  {mod.enabled ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
                  {mod.enabled ? 'Enabled' : 'Disabled'}
                </span>
                {mod.hasSettings && (
                  <button className="mp-settings-btn" onClick={() => setSettingsModule(mod)}>
                    <Settings size={14} />
                    Settings
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Settings Drawer */}
      {settingsModule && (
        <ModuleSettingsModal module={settingsModule} onClose={() => setSettingsModule(null)} />
      )}

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
