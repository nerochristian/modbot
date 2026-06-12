import { useState, useMemo, useCallback } from 'react'
import {
  Search, Settings, X, ChevronRight, Zap, Shield, Brain, ShieldAlert,
  ScrollText, Ticket, MessageSquare, Lock, Eye, Users, Star, Crown,
  Sparkles, BarChart3, Clock, Bell, Trash2, Hash, Mic, Tag, Terminal,
  Smile, Timer, Mail, Image, Heart, Radio, Tv, Video, Bookmark,
  Ban, Gift, FileText, CheckCircle2, XCircle, AlertTriangle,
  SlidersHorizontal, Filter, ArrowUpDown, Loader2, Package
} from 'lucide-react'
import { useGuild } from '../GuildDashboard'
import ModuleSettingsModal from './ModuleSettingsModal'

/* ── Module Data ── */
const MODULES = [
  { id: 'levels', name: 'Levels', description: 'Enables levelling on the guild', category: 'Engagement', icon: BarChart3, color: '#6C5CE7', badges: ['New'], tier: 'Standard', enabled: true, hasSettings: true, setupStatus: 'configured', stats: { users: 1240 } },
  { id: 'tickets', name: 'Tickets', description: 'Support tickets with dashboard-deployed panel, private channels, transcripts, and staff actions.', category: 'Utility', icon: Ticket, color: '#00d68f', badges: ['New'], tier: 'Free', enabled: true, hasSettings: true, setupStatus: 'configured', stats: { open: 3 } },
  { id: 'moderation', name: 'Moderation', description: 'Enabled moderation commands and mod log.', category: 'Moderation', icon: Shield, color: '#ff4d6a', badges: [], tier: 'Free', enabled: true, hasSettings: true, setupStatus: 'configured', stats: { actions: 89 } },
  { id: 'afk', name: 'AFK', description: 'Allow members to set an AFK status.', category: 'Utility', icon: Clock, color: '#a29bfe', badges: [], tier: 'Free', enabled: true, hasSettings: false, setupStatus: 'configured', stats: {} },
  { id: 'autopurge', name: 'Auto Purge', description: 'Automatically purge messages in a channel at configurable times.', category: 'Automation', icon: Trash2, color: '#f97316', badges: [], tier: 'Standard', enabled: false, hasSettings: true, setupStatus: 'needs_setup', stats: {} },
  { id: 'announcements', name: 'Announcements', description: 'Enables join/leave/ban announcements (with options).', category: 'Utility', icon: Bell, color: '#ffb800', badges: [], tier: 'Free', enabled: true, hasSettings: true, setupStatus: 'configured', stats: {} },
  { id: 'actionlog', name: 'Action Log', description: 'Customizable log of events that happen in the server.', category: 'Logging', icon: ScrollText, color: '#00b4d8', badges: [], tier: 'Free', enabled: true, hasSettings: true, setupStatus: 'configured', stats: { events: 2401 } },
  { id: 'automod', name: 'Automod', description: 'Enables various auto moderation features.', category: 'Moderation', icon: Zap, color: '#6C5CE7', badges: [], tier: 'Free', enabled: true, hasSettings: true, setupStatus: 'configured', stats: { blocked: 47 } },
  { id: 'autoresponder', name: 'Autoresponder', description: 'Automatically respond to text triggers.', category: 'Automation', icon: MessageSquare, color: '#e0c3fc', badges: [], tier: 'Free', enabled: false, hasSettings: true, setupStatus: 'needs_setup', stats: {} },
  { id: 'reminders', name: 'Reminders', description: 'Enables members to set reminders.', category: 'Utility', icon: Bell, color: '#00d68f', badges: [], tier: 'Free', enabled: true, hasSettings: false, setupStatus: 'configured', stats: {} },
  { id: 'autoroles', name: 'Autoroles', description: 'Enables auto roles on join, timed auto roles, and joinable ranks.', category: 'Automation', icon: Users, color: '#a29bfe', badges: [], tier: 'Free', enabled: true, hasSettings: true, setupStatus: 'configured', stats: {} },
  { id: 'voicetext', name: 'Voice Text Linking', description: 'Open a text channel when a user joins a voice channel', category: 'Utility', icon: Mic, color: '#00b4d8', badges: [], tier: 'Standard', enabled: false, hasSettings: true, setupStatus: 'needs_setup', stats: {} },
  { id: 'tags', name: 'Tags', description: 'Allow users or some roles to create tags', category: 'Utility', icon: Tag, color: '#ffb800', badges: [], tier: 'Free', enabled: true, hasSettings: true, setupStatus: 'configured', stats: {} },
  { id: 'customcommands', name: 'Custom Commands', description: 'Create custom commands with a variety of options.', category: 'Automation', icon: Terminal, color: '#6C5CE7', badges: [], tier: 'Free', enabled: true, hasSettings: true, setupStatus: 'configured', stats: { commands: 12 } },
  { id: 'fun', name: 'Fun', description: 'Adds fun commands to dyno!', category: 'Engagement', icon: Smile, color: '#f97316', badges: [], tier: 'Free', enabled: true, hasSettings: false, setupStatus: 'configured', stats: {} },
  { id: 'slowmode', name: 'Slowmode', description: 'Rate limit the number of messages members can send in a channel.', category: 'Moderation', icon: Timer, color: '#ff4d6a', badges: [], tier: 'Standard', enabled: false, hasSettings: true, setupStatus: 'needs_setup', stats: {} },
  { id: 'automessage', name: 'Auto Message', description: 'Automatically post timed messages in a channel.', category: 'Automation', icon: Mail, color: '#00d68f', badges: [], tier: 'Free', enabled: false, hasSettings: true, setupStatus: 'needs_setup', stats: {} },
  { id: 'embedder', name: 'Message Embedder', description: 'Post and edit managed embeds in any channel!', category: 'Utility', icon: Image, color: '#a29bfe', badges: [], tier: 'Free', enabled: true, hasSettings: true, setupStatus: 'configured', stats: {} },
  { id: 'welcome', name: 'Welcome', description: 'Create welcome messages with various options.', category: 'Engagement', icon: Heart, color: '#e0c3fc', badges: [], tier: 'Free', enabled: true, hasSettings: true, setupStatus: 'configured', stats: {} },
  { id: 'reddit', name: 'Reddit', description: 'Subscribe to new posts in subreddits.', category: 'Engagement', icon: Radio, color: '#f97316', badges: [], tier: 'Premium', enabled: false, hasSettings: true, setupStatus: 'needs_setup', stats: {} },
  { id: 'autodelete', name: 'Auto Delete', description: 'Automatically delete messages in a channel after users send them.', category: 'Automation', icon: Trash2, color: '#ff4d6a', badges: [], tier: 'Free', enabled: false, hasSettings: true, setupStatus: 'needs_setup', stats: {} },
  { id: 'reactionroles', name: 'Reaction Roles', description: 'Allow members to self-assign roles by reacting.', category: 'Engagement', icon: Star, color: '#ffb800', badges: [], tier: 'Free', enabled: true, hasSettings: true, setupStatus: 'configured', stats: {} },
  { id: 'starboard', name: 'Starboard', description: 'Allows members to save the best posts into a channel by reacting.', category: 'Engagement', icon: Bookmark, color: '#6C5CE7', badges: [], tier: 'Free', enabled: false, hasSettings: true, setupStatus: 'needs_setup', stats: {} },
  { id: 'autoban', name: 'Autoban', description: 'Auto bans user based on a set of rules', category: 'Moderation', icon: Ban, color: '#ff4d6a', badges: [], tier: 'Free', enabled: false, hasSettings: true, setupStatus: 'needs_setup', stats: {} },
  { id: 'giveaways', name: 'Giveaways', description: 'Allows you to host giveaways on your server with Dyno.', category: 'Engagement', icon: Gift, color: '#00d68f', badges: [], tier: 'Free', enabled: false, hasSettings: true, setupStatus: 'needs_setup', stats: {} },
  { id: 'forms', name: 'Forms', description: 'Forms allows you to build your own set of questions for your server members/users to fill out and receive submissions straight into your Discord server!', category: 'Utility', icon: FileText, color: '#00b4d8', badges: [], tier: 'Free', enabled: false, hasSettings: true, setupStatus: 'needs_setup', stats: {} },
  { id: 'twitch', name: 'Twitch', description: 'Notifications when streamers go online', category: 'Engagement', icon: Tv, color: '#9146FF', badges: [], tier: 'Premium', enabled: false, hasSettings: true, setupStatus: 'needs_setup', stats: {} },
  { id: 'youtube', name: 'Youtube', description: 'Notifications when youtubers post videos', category: 'Engagement', icon: Video, color: '#FF0000', badges: [], tier: 'Premium', enabled: false, hasSettings: true, setupStatus: 'needs_setup', stats: {} },
  { id: 'highlights', name: 'Highlights', description: 'Allow members to subscribe to DM notifications for keywords in the server.', category: 'Utility', icon: Sparkles, color: '#ffb800', badges: [], tier: 'Free', enabled: false, hasSettings: false, setupStatus: 'configured', stats: {} },
  { id: 'tiktok', name: 'TikTok', description: 'Notifications when creators posts a new video', category: 'Engagement', icon: Video, color: '#00f2ea', badges: [], tier: 'Premium', enabled: false, hasSettings: true, setupStatus: 'needs_setup', stats: {} },
  { id: 'kick', name: 'Kick', description: 'Notifications when streamers go online.', category: 'Engagement', icon: Tv, color: '#53FC18', badges: [], tier: 'Premium', enabled: false, hasSettings: true, setupStatus: 'needs_setup', stats: {} },
]

const CATEGORIES = ['All', 'Moderation', 'Utility', 'Engagement', 'Logging', 'Automation']
const FILTERS = ['All', 'Enabled', 'Disabled', 'New', 'Standard', 'Premium']
const SORT_OPTIONS = [
  { value: 'name', label: 'Name' },
  { value: 'status', label: 'Status' },
  { value: 'tier', label: 'Tier' },
]

export default function Modules() {
  const { config, updateConfig } = useGuild()
  const [modules, setModules] = useState(MODULES)
  const [search, setSearch] = useState('')
  const [activeCategory, setActiveCategory] = useState('All')
  const [activeFilter, setActiveFilter] = useState('All')
  const [sortBy, setSortBy] = useState('name')
  const [settingsModule, setSettingsModule] = useState(null)
  const [togglingId, setTogglingId] = useState(null)
  const [toast, setToast] = useState(null)

  const showToast = useCallback((message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }, [])

  const handleToggle = useCallback(async (mod) => {
    setTogglingId(mod.id)
    const newEnabled = !mod.enabled
    setModules(prev => prev.map(m => m.id === mod.id ? { ...m, enabled: newEnabled } : m))
    try {
      const key = `${mod.id}_enabled`
      await updateConfig({ [key]: newEnabled })
      showToast(`${mod.name} ${newEnabled ? 'enabled' : 'disabled'}`)
    } catch {
      setModules(prev => prev.map(m => m.id === mod.id ? { ...m, enabled: !newEnabled } : m))
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
    else if (activeFilter === 'New') result = result.filter(m => m.badges.includes('New'))
    else if (activeFilter === 'Standard') result = result.filter(m => m.tier === 'Standard')
    else if (activeFilter === 'Premium') result = result.filter(m => m.tier === 'Premium')

    result.sort((a, b) => {
      if (sortBy === 'status') return (b.enabled ? 1 : 0) - (a.enabled ? 1 : 0)
      if (sortBy === 'tier') {
        const order = { Premium: 0, Standard: 1, Free: 2 }
        return (order[a.tier] ?? 2) - (order[b.tier] ?? 2)
      }
      return a.name.localeCompare(b.name)
    })
    return result
  }, [modules, search, activeCategory, activeFilter, sortBy])

  const counts = useMemo(() => ({
    total: modules.length,
    enabled: modules.filter(m => m.enabled).length,
    premium: modules.filter(m => m.tier === 'Premium').length,
    needsSetup: modules.filter(m => m.setupStatus === 'needs_setup' && m.enabled).length,
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
          <div className="mp-counter"><span className="mp-counter-val mp-c-gold">{counts.premium}</span><span className="mp-counter-lbl">Premium</span></div>
          {counts.needsSetup > 0 && <div className="mp-counter"><span className="mp-counter-val mp-c-orange">{counts.needsSetup}</span><span className="mp-counter-lbl">Setup</span></div>}
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
            {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      </div>

      {/* Filter chips */}
      <div className="mp-filters">
        <div className="mp-chip-group">
          {CATEGORIES.map(c => (
            <button key={c} className={`mp-chip ${activeCategory === c ? 'active' : ''}`} onClick={() => setActiveCategory(c)}>{c}</button>
          ))}
        </div>
        <div className="mp-chip-divider" />
        <div className="mp-chip-group">
          {FILTERS.map(f => (
            <button key={f} className={`mp-chip ${activeFilter === f ? 'active' : ''}`} onClick={() => setActiveFilter(f)}>
              {f === 'Premium' && <Crown size={12} />}
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Module grid */}
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
                <div className="mp-card-icon" style={{ background: `${mod.color}15`, color: mod.color }}>
                  <mod.icon size={20} />
                </div>
                <div className="mp-card-info">
                  <div className="mp-card-name">
                    {mod.name}
                    {mod.badges.map(b => <span key={b} className="mp-badge mp-badge-new">{b}</span>)}
                    {mod.tier === 'Standard' && <span className="mp-badge mp-badge-std">Standard</span>}
                    {mod.tier === 'Premium' && <span className="mp-badge mp-badge-prem"><Crown size={10} />Premium</span>}
                  </div>
                  <div className="mp-card-cat">{mod.category}</div>
                </div>
                <button
                  className={`mp-toggle ${mod.enabled ? 'on' : ''}`}
                  onClick={() => handleToggle(mod)}
                  disabled={togglingId === mod.id}
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

      {/* Settings Modal */}
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
