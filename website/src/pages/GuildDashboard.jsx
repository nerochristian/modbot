import { useState, useEffect } from 'react'
import { Link, useParams, Routes, Route, useLocation } from 'react-router-dom'
import {
  Shield, LayoutDashboard,
  Gavel, Settings, Users, Server,
  Bell, Loader2,
  AlertCircle, ChevronDown, Menu, X, BarChart3, Calendar, List,
  ShieldAlert, AlertTriangle, FileText, RefreshCcw, Database, Puzzle, Star, Search, HelpCircle
} from 'lucide-react'
import { api } from '../api'
import { ThemeToggle } from '../theme'
import VortexLogo from '../components/VortexLogo'
import { GuildContext } from './guild/GuildContext'
import { AreaChart, Area, ResponsiveContainer } from 'recharts'
import Overview from './guild/Overview'
import Modules from './guild/Modules'
import Logging from './guild/Logging'
import Commands from './guild/Commands'
import Cases from './guild/Cases'
import GuildSettings from './guild/GuildSettings'
import {
  AntiRaidDashboard,
  AppealsDashboard,
  BackupDashboard,
  CommandCenter,
  EventsDashboard,
  IntegrationsDashboard,
  LogsDashboard,
  MembersDashboard,
  ModerationDashboard,
  PremiumDashboard,
  WarningsDashboard,
} from './guild/DashboardViews'
import './GuildDashboard.css'

const NAV_ITEMS = [
  { path: '', icon: LayoutDashboard, label: 'Overview', end: true },
  { path: 'dashboard', icon: BarChart3, label: 'Dashboard', badge: 'Beta' },
  { path: 'events', icon: Calendar, label: 'Events' },
  { path: 'logs', icon: List, label: 'Logs' },
  { path: 'automod', icon: Shield, label: 'AutoMod' },
  { path: 'antiraid', icon: ShieldAlert, label: 'Anti-Raid' },
  { path: 'moderation', icon: Gavel, label: 'Moderation' },
  { path: 'members', icon: Users, label: 'Members' },
  { path: 'warnings', icon: AlertTriangle, label: 'Warnings' },
  { path: 'cases', icon: FileText, label: 'Cases' },
  { path: 'appeals', icon: RefreshCcw, label: 'Appeals' },
  { path: 'backup', icon: Database, label: 'Server Backup' },
  { path: 'settings', icon: Settings, label: 'Settings' },
  { path: 'integrations', icon: Puzzle, label: 'Integrations' },
  { path: 'premium', icon: Star, label: 'Premium' },
]

export default function GuildDashboard() {
  const { guildId } = useParams()
  const location = useLocation()
  const [guild, setGuild] = useState(null)
  const [config, setConfig] = useState(null)
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    Promise.all([
      api.getMe(),
      api.getGuild(guildId),
      api.getGuildConfig(guildId),
    ])
      .then(([me, g, c]) => {
        setUser(me)
        setGuild(g)
        setConfig(c)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [guildId])

  const refreshConfig = async () => {
    const c = await api.getGuildConfig(guildId).catch(() => null)
    if (c) setConfig(c)
  }

  const updateConfig = async (updates) => {
    const c = await api.updateGuildConfig(guildId, updates)
    setConfig(c)
    return c
  }

  const currentPath = location.pathname.split(`/dashboard/${guildId}`)[1]?.replace(/^\//, '') || ''

  if (loading) {
    return (
      <div className="dash-loading">
        <Loader2 size={40} className="spin" />
        <p>Loading server dashboard...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="dash-loading">
        <AlertCircle size={40} />
        <p>{error}</p>
        <Link to="/dashboard" className="btn btn-primary btn-sm">Back to Servers</Link>
      </div>
    )
  }

  return (
    <GuildContext.Provider value={{ guild, config, guildId, refreshConfig, updateConfig }}>
      <div className="guild-dashboard">
        {/* Mobile toggle */}
        <button
          className="sidebar-toggle btn-icon"
          onClick={() => setSidebarOpen(!sidebarOpen)}
        >
          {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>

        {/* Sidebar */}
        <aside className={`gd-sidebar glass-strong ${sidebarOpen ? 'open' : ''}`}>
          <div className="gd-sidebar-top">
            <Link to="/" className="gd-brand">
              <div className="gd-brand-icon">
                <VortexLogo size={22} />
              </div>
              <div className="gd-brand-text">
                <span className="gd-brand-title">VORTEX</span>
                <span className="gd-brand-subtitle">MODERATION</span>
              </div>
            </Link>
          </div>

          <nav className="gd-nav">
            {NAV_ITEMS.map(item => {
              const isActive = item.end
                ? currentPath === ''
                : currentPath.startsWith(item.path)
              return (
                <Link
                  key={item.path}
                  to={`/dashboard/${guildId}${item.path ? `/${item.path}` : ''}`}
                  className={`gd-nav-item ${isActive ? 'active' : ''}`}
                  onClick={() => setSidebarOpen(false)}
                >
                  <item.icon size={18} />
                  <span>{item.label}</span>
                  {item.badge && <span className="gd-nav-badge">{item.badge}</span>}
                  {isActive && <div className="gd-nav-indicator" />}
                </Link>
              )
            })}
          </nav>

          <div className="gd-sidebar-bottom">
            <div className="gd-vortex-status">
              <div className="vtx-stat-header">
                <div className="vtx-stat-dot"></div>
                <span>Vortex Status</span>
              </div>
              <div className="vtx-stat-sub">All Systems Operational</div>
              <div className="vtx-uptime-box">
                <div className="vtx-uptime-header">
                  <span>Uptime</span>
                  <span className="vtx-uptime-val">99.99%</span>
                </div>
                <div className="vtx-uptime-chart" style={{height:'30px'}}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={[
                      {val: 20}, {val: 15}, {val: 22}, {val: 10}, 
                      {val: 18}, {val: 8}, {val: 12}, {val: 5}, 
                      {val: 15}, {val: 8}, {val: 2}
                    ]}>
                      <defs>
                        <linearGradient id="upGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#10b981" stopOpacity={0.4}/>
                          <stop offset="100%" stopColor="#10b981" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <Area type="monotone" dataKey="val" stroke="#10b981" strokeWidth={2} fill="url(#upGrad)" isAnimationActive={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        </aside>

        {/* Overlay for mobile */}
        {sidebarOpen && (
          <div className="gd-overlay" onClick={() => setSidebarOpen(false)} />
        )}

        {/* Topbar & Main Wrapper */}
        <div className="gd-content-wrapper">
          <header className="gd-topbar">
            <div className="gd-tb-left">
              <button className="sidebar-toggle btn-icon" onClick={() => setSidebarOpen(!sidebarOpen)}>
                <Menu size={20} />
              </button>
              
              <div className="gd-server-selector">
                <div className="gd-ss-icon">
                  {guild?.icon ? <img src={guild.icon} alt="" /> : <Server size={14} />}
                </div>
                <span className="gd-ss-name">{guild?.name}</span>
                <ChevronDown size={14} className="gd-ss-arrow" />
              </div>
            </div>

            <div className="gd-tb-center">
              <div className="gd-search-box">
                <Search size={16} />
                <input type="text" placeholder="Search anything..." />
                <span className="gd-search-key">⌘K</span>
              </div>
            </div>

            <div className="gd-tb-right">
              <ThemeToggle className="gd-theme-toggle" />
              <button className="btn-icon"><HelpCircle size={18} /></button>
              <button className="btn-icon gd-notif-btn">
                <Bell size={18} />
                <span className="gd-notif-badge">3</span>
              </button>
              <div className="gd-user-dropdown">
                {user?.avatar ? (
                  <img src={user.avatar} alt="" className="gd-user-avatar" />
                ) : (
                  <div className="gd-user-avatar-ph">{user?.username?.[0]?.toUpperCase()}</div>
                )}
                <div className="gd-user-info">
                  <span className="gd-user-name">{user?.globalName || user?.username}</span>
                  <span className="gd-user-tag">Server Owner</span>
                </div>
              </div>
            </div>
          </header>

        {/* Main Content */}
          <main className="gd-main">
            <Routes>
              <Route index element={<Overview />} />
              <Route path="dashboard" element={<CommandCenter />} />
              <Route path="events" element={<EventsDashboard />} />
              <Route path="logs" element={<LogsDashboard />} />
              <Route path="automod" element={<Modules />} />
              <Route path="antiraid" element={<AntiRaidDashboard />} />
              <Route path="moderation" element={<ModerationDashboard />} />
              <Route path="members" element={<MembersDashboard />} />
              <Route path="warnings" element={<WarningsDashboard />} />
              <Route path="commands" element={<Commands />} />
              <Route path="logging" element={<Logging />} />
              <Route path="cases" element={<Cases />} />
              <Route path="appeals" element={<AppealsDashboard />} />
              <Route path="backup" element={<BackupDashboard />} />
              <Route path="settings" element={<GuildSettings />} />
              <Route path="integrations" element={<IntegrationsDashboard />} />
              <Route path="premium" element={<PremiumDashboard />} />
              <Route path="*" element={<Overview />} />
            </Routes>
          </main>
        </div>
      </div>
    </GuildContext.Provider>
  )
}
