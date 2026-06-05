import { useState, useEffect, createContext, useContext } from 'react'
import { Link, useParams, useNavigate, Routes, Route, useLocation } from 'react-router-dom'
import {
  Shield, LogOut, ChevronLeft, LayoutDashboard, Zap, Brain,
  ScrollText, Ticket, Gavel, Settings, Users, Server,
  Bell, Eye, ShieldCheck, MessageSquare, Lock, Loader2,
  AlertCircle, ChevronDown, Menu, X
} from 'lucide-react'
import { api } from '../api'
import Overview from './guild/Overview'
import Modules from './guild/Modules'
import Logging from './guild/Logging'
import Cases from './guild/Cases'
import GuildSettings from './guild/GuildSettings'
import './GuildDashboard.css'

const GuildContext = createContext(null)
export const useGuild = () => useContext(GuildContext)

const NAV_ITEMS = [
  { path: '', icon: LayoutDashboard, label: 'Overview', end: true },
  { path: 'modules', icon: Zap, label: 'Modules' },
  { path: 'logging', icon: ScrollText, label: 'Logging' },
  { path: 'cases', icon: Gavel, label: 'Cases' },
  { path: 'settings', icon: Settings, label: 'Settings' },
]

export default function GuildDashboard() {
  const { guildId } = useParams()
  const navigate = useNavigate()
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
    try {
      const c = await api.getGuildConfig(guildId)
      setConfig(c)
    } catch {}
  }

  const updateConfig = async (updates) => {
    try {
      const c = await api.updateGuildConfig(guildId, updates)
      setConfig(c)
      return c
    } catch (err) {
      throw err
    }
  }

  const handleLogout = async () => {
    await api.logout().catch(() => {})
    navigate('/')
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
            <Link to="/dashboard" className="gd-back">
              <ChevronLeft size={16} />
              <span>All Servers</span>
            </Link>
            <div className="gd-guild-header">
              <div className="gd-guild-icon">
                {guild?.icon ? (
                  <img src={guild.icon} alt="" />
                ) : (
                  <div className="gd-guild-placeholder">
                    {guild?.name?.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()}
                  </div>
                )}
              </div>
              <div className="gd-guild-info">
                <span className="gd-guild-name">{guild?.name}</span>
                <span className="gd-guild-members">
                  <Users size={12} />
                  {(guild?.memberCount || 0).toLocaleString()}
                </span>
              </div>
            </div>
          </div>

          <nav className="gd-nav">
            <div className="gd-nav-label">Dashboard</div>
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
                  {isActive && <div className="gd-nav-indicator" />}
                </Link>
              )
            })}
          </nav>

          <div className="gd-sidebar-bottom">
            <div className="gd-user-card">
              {user?.avatar ? (
                <img src={user.avatar} alt="" className="gd-user-avatar" />
              ) : (
                <div className="gd-user-avatar-ph">
                  {user?.username?.[0]?.toUpperCase()}
                </div>
              )}
              <div className="gd-user-info">
                <span className="gd-user-name">{user?.globalName || user?.username}</span>
                <span className="gd-user-tag">@{user?.username}</span>
              </div>
              <button className="btn-icon gd-logout" onClick={handleLogout} title="Logout">
                <LogOut size={16} />
              </button>
            </div>
          </div>
        </aside>

        {/* Overlay for mobile */}
        {sidebarOpen && (
          <div className="gd-overlay" onClick={() => setSidebarOpen(false)} />
        )}

        {/* Main Content */}
        <main className="gd-main">
          <Routes>
            <Route index element={<Overview />} />
            <Route path="modules" element={<Modules />} />
            <Route path="logging" element={<Logging />} />
            <Route path="cases" element={<Cases />} />
            <Route path="settings" element={<GuildSettings />} />
          </Routes>
        </main>
      </div>
    </GuildContext.Provider>
  )
}
