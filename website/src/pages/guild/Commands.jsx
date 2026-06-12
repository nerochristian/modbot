import { useState, useMemo, useCallback } from 'react'
import {
  Search, X, ChevronRight, ChevronDown, Shield, Zap, Brain,
  Gavel, Ticket, MessageSquare, Users, Settings, Ban, UserMinus,
  VolumeX, AlertTriangle, Trash2, Lock, Unlock, Eye, Clock,
  Hash, Star, Crown, CheckCircle2, XCircle, Terminal, Filter,
  ArrowUpDown, Package, BarChart3, Smile, Bell, Tag, Heart,
  Gift, FileText, Image, Timer, Radio
} from 'lucide-react'
import { useGuild } from '../GuildDashboard'

const COMMANDS = [
  // Moderation
  { id: 'ban', name: 'ban', description: 'Ban a member from the server', module: 'Moderation', category: 'Moderation', enabled: true, permission: 'Ban Members', cooldown: 0, usage: '/ban <user> [reason] [days]' },
  { id: 'kick', name: 'kick', description: 'Kick a member from the server', module: 'Moderation', category: 'Moderation', enabled: true, permission: 'Kick Members', cooldown: 0, usage: '/kick <user> [reason]' },
  { id: 'mute', name: 'mute', description: 'Timeout a member', module: 'Moderation', category: 'Moderation', enabled: true, permission: 'Moderate Members', cooldown: 0, usage: '/mute <user> <duration> [reason]' },
  { id: 'unmute', name: 'unmute', description: 'Remove timeout from a member', module: 'Moderation', category: 'Moderation', enabled: true, permission: 'Moderate Members', cooldown: 0, usage: '/unmute <user>' },
  { id: 'warn', name: 'warn', description: 'Warn a member', module: 'Moderation', category: 'Moderation', enabled: true, permission: 'Manage Messages', cooldown: 0, usage: '/warn <user> <reason>' },
  { id: 'warnings', name: 'warnings', description: 'View warnings for a member', module: 'Moderation', category: 'Moderation', enabled: true, permission: 'Manage Messages', cooldown: 3, usage: '/warnings <user>' },
  { id: 'purge', name: 'purge', description: 'Bulk delete messages in a channel', module: 'Moderation', category: 'Moderation', enabled: true, permission: 'Manage Messages', cooldown: 5, usage: '/purge <amount> [user]' },
  { id: 'lockdown', name: 'lockdown', description: 'Lock or unlock a channel', module: 'Moderation', category: 'Moderation', enabled: true, permission: 'Manage Channels', cooldown: 0, usage: '/lockdown [channel]' },
  { id: 'slowmode_cmd', name: 'slowmode', description: 'Set channel slowmode', module: 'Moderation', category: 'Moderation', enabled: true, permission: 'Manage Channels', cooldown: 0, usage: '/slowmode <seconds> [channel]' },
  { id: 'case', name: 'case', description: 'View a moderation case', module: 'Moderation', category: 'Moderation', enabled: true, permission: 'Manage Messages', cooldown: 3, usage: '/case <id>' },
  // Automod
  { id: 'automod_toggle', name: 'automod', description: 'Toggle automod features', module: 'Automod', category: 'Moderation', enabled: true, permission: 'Manage Server', cooldown: 0, usage: '/automod <feature> <on/off>' },
  { id: 'blacklist', name: 'blacklist', description: 'Manage word blacklist', module: 'Automod', category: 'Moderation', enabled: true, permission: 'Manage Server', cooldown: 0, usage: '/blacklist <add/remove> <word>' },
  // Utility
  { id: 'help', name: 'help', description: 'Show available commands', module: 'Core', category: 'Utility', enabled: true, permission: 'Send Messages', cooldown: 5, usage: '/help [command]' },
  { id: 'serverinfo', name: 'serverinfo', description: 'Display server information', module: 'Core', category: 'Utility', enabled: true, permission: 'Send Messages', cooldown: 10, usage: '/serverinfo' },
  { id: 'userinfo', name: 'userinfo', description: 'Display user information', module: 'Core', category: 'Utility', enabled: true, permission: 'Send Messages', cooldown: 5, usage: '/userinfo [user]' },
  { id: 'avatar', name: 'avatar', description: 'Get a user\'s avatar', module: 'Core', category: 'Utility', enabled: true, permission: 'Send Messages', cooldown: 5, usage: '/avatar [user]' },
  { id: 'role', name: 'role', description: 'Add or remove a role from a member', module: 'Core', category: 'Utility', enabled: true, permission: 'Manage Roles', cooldown: 0, usage: '/role <user> <role>' },
  { id: 'tag', name: 'tag', description: 'Use or manage tags', module: 'Tags', category: 'Utility', enabled: true, permission: 'Send Messages', cooldown: 3, usage: '/tag <name>' },
  { id: 'embed', name: 'embed', description: 'Create or edit an embed message', module: 'Embedder', category: 'Utility', enabled: true, permission: 'Manage Messages', cooldown: 5, usage: '/embed <channel>' },
  { id: 'remind', name: 'remind', description: 'Set a reminder', module: 'Reminders', category: 'Utility', enabled: true, permission: 'Send Messages', cooldown: 10, usage: '/remind <time> <message>' },
  { id: 'afk_cmd', name: 'afk', description: 'Set your AFK status', module: 'AFK', category: 'Utility', enabled: true, permission: 'Send Messages', cooldown: 30, usage: '/afk [message]' },
  { id: 'poll', name: 'poll', description: 'Create a poll', module: 'Core', category: 'Utility', enabled: true, permission: 'Send Messages', cooldown: 10, usage: '/poll <question> <options>' },
  // Engagement
  { id: 'rank', name: 'rank', description: 'View your level and rank', module: 'Levels', category: 'Engagement', enabled: true, permission: 'Send Messages', cooldown: 10, usage: '/rank [user]' },
  { id: 'leaderboard', name: 'leaderboard', description: 'View the level leaderboard', module: 'Levels', category: 'Engagement', enabled: true, permission: 'Send Messages', cooldown: 15, usage: '/leaderboard' },
  { id: 'giveaway_cmd', name: 'giveaway', description: 'Start or manage giveaways', module: 'Giveaways', category: 'Engagement', enabled: false, permission: 'Manage Server', cooldown: 0, usage: '/giveaway start <prize> <duration>' },
  // Fun
  { id: 'meme', name: 'meme', description: 'Get a random meme', module: 'Fun', category: 'Fun', enabled: true, permission: 'Send Messages', cooldown: 10, usage: '/meme' },
  { id: '8ball', name: '8ball', description: 'Ask the magic 8-ball', module: 'Fun', category: 'Fun', enabled: true, permission: 'Send Messages', cooldown: 5, usage: '/8ball <question>' },
  { id: 'coinflip', name: 'coinflip', description: 'Flip a coin', module: 'Fun', category: 'Fun', enabled: true, permission: 'Send Messages', cooldown: 3, usage: '/coinflip' },
]

const CMD_CATEGORIES = ['All', 'Moderation', 'Utility', 'Engagement', 'Fun']

export default function Commands() {
  const { config, updateConfig } = useGuild()
  const [commands, setCommands] = useState(COMMANDS)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('All')
  const [filter, setFilter] = useState('All')
  const [expandedId, setExpandedId] = useState(null)
  const [toast, setToast] = useState(null)

  const showToast = useCallback((msg, type = 'success') => {
    setToast({ message: msg, type })
    setTimeout(() => setToast(null), 3000)
  }, [])

  const handleToggle = useCallback(async (cmd) => {
    const newVal = !cmd.enabled
    setCommands(prev => prev.map(c => c.id === cmd.id ? { ...c, enabled: newVal } : c))
    try {
      await updateConfig({ [`cmd_${cmd.id}_enabled`]: newVal })
      showToast(`/${cmd.name} ${newVal ? 'enabled' : 'disabled'}`)
    } catch {
      setCommands(prev => prev.map(c => c.id === cmd.id ? { ...c, enabled: !newVal } : c))
      showToast('Failed to update', 'error')
    }
  }, [updateConfig, showToast])

  const filtered = useMemo(() => {
    let result = [...commands]
    if (search) {
      const q = search.toLowerCase()
      result = result.filter(c => c.name.includes(q) || c.description.toLowerCase().includes(q) || c.module.toLowerCase().includes(q))
    }
    if (category !== 'All') result = result.filter(c => c.category === category)
    if (filter === 'Enabled') result = result.filter(c => c.enabled)
    else if (filter === 'Disabled') result = result.filter(c => !c.enabled)
    return result.sort((a, b) => a.name.localeCompare(b.name))
  }, [commands, search, category, filter])

  const counts = useMemo(() => ({
    total: commands.length,
    enabled: commands.filter(c => c.enabled).length,
    disabled: commands.filter(c => !c.enabled).length,
  }), [commands])

  return (
    <div className="mp">
      <div className="mp-header">
        <div>
          <h1 className="page-title">Commands</h1>
          <p className="page-subtitle">Manage individual command access, permissions, and cooldowns.</p>
        </div>
        <div className="mp-counters">
          <div className="mp-counter"><span className="mp-counter-val">{counts.total}</span><span className="mp-counter-lbl">Total</span></div>
          <div className="mp-counter"><span className="mp-counter-val mp-c-green">{counts.enabled}</span><span className="mp-counter-lbl">Enabled</span></div>
          <div className="mp-counter"><span className="mp-counter-val mp-c-orange">{counts.disabled}</span><span className="mp-counter-lbl">Disabled</span></div>
        </div>
      </div>

      <div className="mp-toolbar">
        <div className="mp-search">
          <Search size={16} />
          <input type="text" placeholder="Search commands..." value={search} onChange={e => setSearch(e.target.value)} />
          {search && <button className="mp-search-clear" onClick={() => setSearch('')}><X size={14} /></button>}
        </div>
      </div>

      <div className="mp-filters">
        <div className="mp-chip-group">
          {CMD_CATEGORIES.map(c => (
            <button key={c} className={`mp-chip ${category === c ? 'active' : ''}`} onClick={() => setCategory(c)}>{c}</button>
          ))}
        </div>
        <div className="mp-chip-divider" />
        <div className="mp-chip-group">
          {['All', 'Enabled', 'Disabled'].map(f => (
            <button key={f} className={`mp-chip ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>{f}</button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="empty-state">
          <Terminal size={48} />
          <h3>No commands found</h3>
          <p>Try adjusting your search or filters.</p>
        </div>
      ) : (
        <div className="cmd-list">
          {filtered.map(cmd => (
            <div className={`cmd-row ${cmd.enabled ? '' : 'cmd-row-off'} ${expandedId === cmd.id ? 'cmd-row-expanded' : ''}`} key={cmd.id}>
              <div className="cmd-row-main" onClick={() => setExpandedId(expandedId === cmd.id ? null : cmd.id)}>
                <div className="cmd-row-left">
                  <Terminal size={15} className="cmd-icon" />
                  <span className="cmd-name">/{cmd.name}</span>
                  <span className="cmd-module-tag">{cmd.module}</span>
                </div>
                <div className="cmd-row-right">
                  <span className="cmd-perm">{cmd.permission}</span>
                  {cmd.cooldown > 0 && <span className="cmd-cd"><Clock size={11} />{cmd.cooldown}s</span>}
                  <button
                    className={`mp-toggle mp-toggle-sm ${cmd.enabled ? 'on' : ''}`}
                    onClick={e => { e.stopPropagation(); handleToggle(cmd) }}
                    aria-label={cmd.enabled ? `Disable /${cmd.name}` : `Enable /${cmd.name}`}
                  >
                    <span className="mp-toggle-thumb" />
                  </button>
                  <ChevronDown size={14} className={`cmd-chevron ${expandedId === cmd.id ? 'cmd-chevron-open' : ''}`} />
                </div>
              </div>
              {expandedId === cmd.id && (
                <div className="cmd-details">
                  <div className="cmd-detail-row">
                    <span className="cmd-detail-label">Description</span>
                    <span>{cmd.description}</span>
                  </div>
                  <div className="cmd-detail-row">
                    <span className="cmd-detail-label">Usage</span>
                    <code className="cmd-usage">{cmd.usage}</code>
                  </div>
                  <div className="cmd-detail-row">
                    <span className="cmd-detail-label">Permission</span>
                    <span className="cmd-perm">{cmd.permission}</span>
                  </div>
                  <div className="cmd-detail-row">
                    <span className="cmd-detail-label">Cooldown</span>
                    <span>{cmd.cooldown > 0 ? `${cmd.cooldown} seconds` : 'None'}</span>
                  </div>
                  <div className="cmd-detail-row">
                    <span className="cmd-detail-label">Status</span>
                    <span className={`mp-status ${cmd.enabled ? 'mp-status-on' : 'mp-status-off'}`}>
                      {cmd.enabled ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
                      {cmd.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
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
