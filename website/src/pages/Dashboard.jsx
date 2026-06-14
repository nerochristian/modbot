import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Server, Loader2, Plus, ChevronRight, Users } from 'lucide-react'
import { api } from '../api'
import VortexLogo from '../components/VortexLogo'
import './Dashboard.css'

export default function Dashboard() {
  const [user, setUser] = useState(null)
  const [guilds, setGuilds] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getMe()
      .then(data => { setUser(data); setGuilds(data.guilds || []) })
      .catch(() => { window.location.href = '/auth/login' })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="dash-loading">
        <Loader2 size={40} className="spin" />
        <p>Loading your servers...</p>
      </div>
    )
  }

  const managed = guilds.filter(g => g.botInstalled)
  const available = guilds.filter(g => !g.botInstalled && g.canManage)

  return (
    <div className="dash-page">
      <header className="dash-topbar">
        <Link to="/" className="dash-brand">
          <div className="dash-brand-icon"><VortexLogo size={22} /></div>
          VORTEX <span style={{fontWeight:400,fontSize:'0.7rem',letterSpacing:'0.1em',opacity:0.5,marginLeft:4}}>MODERATION</span>
        </Link>
        <div className="dash-user">
          {user?.avatar
            ? <img src={user.avatar} alt="" className="dash-user-av" />
            : <div className="dash-user-ph">{user?.username?.[0]?.toUpperCase()}</div>
          }
          <span className="dash-user-name">{user?.globalName || user?.username}</span>
        </div>
      </header>

      <div className="dash-content">
        <div className="dash-header">
          <h1>Select a Server</h1>
          <p>Choose a server to manage with Vortex Moderation</p>
        </div>

        <div className="dash-grid">
          {managed.map(g => (
            <Link key={g.id} to={`/dashboard/${g.id}`} className="dash-guild-card">
              <div className="dash-guild-icon">
                {g.icon ? <img src={g.icon} alt="" /> : <Server size={20} />}
              </div>
              <div className="dash-guild-info">
                <div className="dash-guild-name">{g.name}</div>
                <div className="dash-guild-meta">
                  <Users size={11} style={{display:'inline',verticalAlign:'middle',marginRight:4}} />
                  {g.memberCount?.toLocaleString() || '—'} members
                </div>
              </div>
              <ChevronRight size={16} className="dash-guild-arrow" />
            </Link>
          ))}

          {available.map(g => (
            <a key={g.id} href={`/auth/invite?guild_id=${g.id}`} className="dash-invite-card">
              <div className="dash-invite-icon"><Plus size={20} /></div>
              <div className="dash-invite-text">
                <strong>{g.name}</strong>
                Add Vortex to this server
              </div>
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}
