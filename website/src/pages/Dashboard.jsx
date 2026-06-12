import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  LogOut, Server, Users, ChevronRight,
  Bot, Plus, Search, Loader2, AlertCircle,
  ShieldCheck, Activity, Zap, Database, BarChart3
} from 'lucide-react'
import { api } from '../api'
import { ThemeToggle } from '../theme'
import VortexLogo from '../components/VortexLogo'
import './Dashboard.css'

export default function Dashboard() {
  const [user, setUser] = useState(null)
  const [guilds, setGuilds] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    api.getMe()
      .then(data => {
        setUser(data)
        setGuilds(data.guilds || [])
      })
      .catch(err => {
        setError(err.message)
      })
      .finally(() => setLoading(false))
  }, [])

  const handleLogout = async () => {
    await api.logout().catch(() => {})
    navigate('/')
  }

  const filtered = guilds.filter(g =>
    g.name.toLowerCase().includes(search.toLowerCase())
  )

  const installed = filtered.filter(g => g.botInstalled)
  const notInstalled = filtered.filter(g => !g.botInstalled && g.canManage)
  const manageableCount = guilds.filter(g => g.botInstalled || g.canManage).length

  if (loading) {
    return (
      <div className="dash-loading">
        <Loader2 size={40} className="spin" />
        <p>Loading your servers...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="dash-loading">
        <AlertCircle size={40} />
        <p>Failed to load. Please <a href="/auth/login">login again</a>.</p>
      </div>
    )
  }

  return (
    <div className="dashboard-page">
      {/* Top bar */}
      <header className="dash-topbar glass-strong">
        <Link to="/" className="nav-brand">
          <div className="nav-logo"><VortexLogo size={22} /></div>
          <span className="nav-name">VORTEX <em>MODERATION</em></span>
        </Link>
        <div className="dash-topbar-right">
          <ThemeToggle />
          {user && (
            <div className="dash-user">
              {user.avatar ? (
                <img src={user.avatar} alt="" className="dash-avatar" />
              ) : (
                <div className="dash-avatar-placeholder">
                  {user.username?.[0]?.toUpperCase()}
                </div>
              )}
              <span className="dash-username">{user.globalName || user.username}</span>
            </div>
          )}
          <button className="btn btn-ghost btn-sm" onClick={handleLogout}>
            <LogOut size={16} />
            Logout
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="dash-content">
        <div className="dash-command">
          <section className="dash-hero">
            <div className="dash-kicker">
              <VortexLogo size={16} />
              Server command center
            </div>
            <h1>Select a Server</h1>
            <p>Choose a server to manage protection, automation, moderation logs, backups, and staff workflows from one Vortex dashboard.</p>
            <div className="dash-hero-stats">
              <div><strong>{installed.length}</strong><span>Protected</span></div>
              <div><strong>{notInstalled.length}</strong><span>Ready to invite</span></div>
              <div><strong>{manageableCount}</strong><span>Manageable</span></div>
            </div>
          </section>

          <aside className="dash-preview" aria-label="Vortex dashboard preview">
            <div className="dash-preview-top">
              <div className="dash-preview-brand">
                <div className="dash-preview-logo"><VortexLogo size={22} /></div>
                <div>
                  <span>Live Protection</span>
                  <small>All systems operational</small>
                </div>
              </div>
              <span className="dash-live-pill">Online</span>
            </div>
            <div className="dash-preview-grid">
              <div className="dash-preview-card">
                <ShieldCheck size={18} />
                <strong>247</strong>
                <span>Threats blocked</span>
              </div>
              <div className="dash-preview-card">
                <Activity size={18} />
                <strong>18</strong>
                <span>Active cases</span>
              </div>
              <div className="dash-preview-card">
                <Zap size={18} />
                <strong>892</strong>
                <span>Auto actions</span>
              </div>
            </div>
            <div className="dash-preview-chart">
              <BarChart3 size={16} />
              <div className="dash-chart-bars">
                {[34, 58, 42, 76, 63, 89, 70, 96, 66, 82].map((height, index) => (
                  <span key={index} style={{ height: `${height}%` }} />
                ))}
              </div>
            </div>
            <div className="dash-preview-row">
              <Database size={16} />
              <span>Backup completed 2m ago</span>
              <strong>Ready</strong>
            </div>
          </aside>
        </div>

        <div className="dash-search-bar">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search servers..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="input"
          />
        </div>

        {installed.length > 0 && (
          <section className="dash-guild-section">
            <h2 className="dash-section-title">
              <Server size={18} />
              Your Servers
              <span className="badge badge-primary">{installed.length}</span>
            </h2>
            <div className="guild-grid">
              {installed.map(g => (
                <Link
                  to={`/dashboard/${g.id}`}
                  className="guild-card card"
                  key={g.id}
                >
                  <div className="guild-card-icon">
                    {g.icon ? (
                      <img src={g.icon} alt="" />
                    ) : (
                      <div className="guild-card-placeholder">
                        {g.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()}
                      </div>
                    )}
                  </div>
                  <div className="guild-card-info">
                    <span className="guild-card-name">{g.name}</span>
                    <span className="guild-card-members">
                      <Users size={13} />
                      {(g.memberCount || 0).toLocaleString()} members
                    </span>
                  </div>
                  <div className="guild-card-arrow">
                    <ChevronRight size={18} />
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}

        {notInstalled.length > 0 && (
          <section className="dash-guild-section">
            <h2 className="dash-section-title">
              <Plus size={18} />
              Add Vortex Moderation
            </h2>
            <div className="guild-grid">
              {notInstalled.map(g => (
                <a
                  href={`/auth/invite?bot=true&guild_id=${g.id}`}
                  className="guild-card card guild-card-invite"
                  key={g.id}
                >
                  <div className="guild-card-icon">
                    {g.icon ? (
                      <img src={g.icon} alt="" />
                    ) : (
                      <div className="guild-card-placeholder">
                        {g.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()}
                      </div>
                    )}
                  </div>
                  <div className="guild-card-info">
                    <span className="guild-card-name">{g.name}</span>
                    <span className="guild-card-members not-installed">
                      <Bot size={13} />
                      Not installed
                    </span>
                  </div>
                  <div className="guild-card-action">
                    <span className="btn btn-primary btn-sm">Invite</span>
                  </div>
                </a>
              ))}
            </div>
          </section>
        )}

        {filtered.length === 0 && !loading && (
          <div className="dash-empty">
            <Server size={48} />
            <h3>No servers found</h3>
            <p>Try a different search or make sure you have Manage Server permission.</p>
          </div>
        )}
      </main>
    </div>
  )
}
