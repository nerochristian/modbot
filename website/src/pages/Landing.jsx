import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  Shield, Zap, Brain, Users, BarChart3, Ticket,
  ChevronRight, Star, ArrowRight, Bot, Lock,
  Eye, MessageSquare, Gavel, ShieldCheck, Sparkles,
  Globe, Server, CheckCircle2, ExternalLink
} from 'lucide-react'
import './Landing.css'

const FEATURES = [
  {
    icon: Shield,
    title: 'Auto Moderation',
    desc: 'Intelligent spam, link, invite, and content filtering with customizable thresholds and actions.',
    color: '#6C5CE7',
  },
  {
    icon: Brain,
    title: 'AI Moderation',
    desc: 'Gemini-powered AI that understands context, detects toxicity, and takes autonomous action.',
    color: '#00b4d8',
  },
  {
    icon: Lock,
    title: 'Anti-Raid',
    desc: 'Real-time raid detection with automatic lockdown, account age filtering, and quarantine.',
    color: '#ff4d6a',
  },
  {
    icon: Eye,
    title: 'Advanced Logging',
    desc: 'Beautiful rich embeds for every server event — messages, members, roles, voice, and more.',
    color: '#ffb800',
  },
  {
    icon: Ticket,
    title: 'Ticket System',
    desc: 'Full support workflow with categories, transcripts, priority routing, and staff claims.',
    color: '#00d68f',
  },
  {
    icon: MessageSquare,
    title: 'Modmail',
    desc: 'Private DM bridge between users and staff with threaded conversations and logs.',
    color: '#e0c3fc',
  },
  {
    icon: ShieldCheck,
    title: 'Verification',
    desc: 'Configurable verification gate with optional voice verification and role assignment.',
    color: '#a29bfe',
  },
  {
    icon: Gavel,
    title: 'Full Moderation',
    desc: 'Ban, kick, mute, warn, purge, lockdown — with case tracking, reasons, and appeal system.',
    color: '#f97316',
  },
  {
    icon: BarChart3,
    title: 'Web Dashboard',
    desc: 'Beautiful panel to configure everything — modules, commands, permissions, and logging.',
    color: '#6C5CE7',
  },
]

const STATS = [
  { value: '99.9%', label: 'Uptime' },
  { value: '<50ms', label: 'Response Time' },
  { value: '100+', label: 'Commands' },
  { value: '24/7', label: 'Protection' },
]

export default function Landing() {
  const heroRef = useRef(null)

  useEffect(() => {
    const handleMouse = (e) => {
      if (!heroRef.current) return
      const { clientX, clientY } = e
      const { innerWidth, innerHeight } = window
      const x = (clientX / innerWidth - 0.5) * 20
      const y = (clientY / innerHeight - 0.5) * 20
      heroRef.current.style.setProperty('--mouse-x', `${x}px`)
      heroRef.current.style.setProperty('--mouse-y', `${y}px`)
    }
    window.addEventListener('mousemove', handleMouse)
    return () => window.removeEventListener('mousemove', handleMouse)
  }, [])

  return (
    <div className="landing">
      {/* ── Navbar ── */}
      <nav className="landing-nav glass-strong">
        <div className="container nav-inner">
          <Link to="/" className="nav-brand">
            <div className="nav-logo">
              <Shield size={24} />
            </div>
            <span className="nav-name">ModBot</span>
            <span className="badge badge-primary">v3.4</span>
          </Link>
          <div className="nav-links">
            <a href="#features" className="nav-link">Features</a>
            <a href="#modules" className="nav-link">Modules</a>
            <a href="#stats" className="nav-link">Stats</a>
            <a href="https://discord.gg/modbot" className="nav-link" target="_blank" rel="noopener">Support</a>
          </div>
          <div className="nav-actions">
            <a href="/auth/login" className="btn btn-ghost btn-sm">Login</a>
            <a href="/auth/invite" className="btn btn-primary btn-sm">
              <Bot size={16} />
              Add to Server
            </a>
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="hero" ref={heroRef}>
        <div className="hero-bg">
          <div className="hero-orb hero-orb-1" />
          <div className="hero-orb hero-orb-2" />
          <div className="hero-orb hero-orb-3" />
          <div className="hero-grid" />
        </div>
        <div className="container hero-content">
          <div className="hero-badge animate-in">
            <Sparkles size={14} />
            <span>Powered by AI • Trusted by thousands</span>
          </div>
          <h1 className="hero-title animate-in" style={{ animationDelay: '0.1s' }}>
            The most powerful
            <br />
            <span className="gradient-text">Discord moderation</span>
            <br />
            bot ever built.
          </h1>
          <p className="hero-subtitle animate-in" style={{ animationDelay: '0.2s' }}>
            Auto-moderation, AI-powered content analysis, anti-raid protection,
            tickets, logging, and a beautiful web dashboard — all in one bot.
          </p>
          <div className="hero-actions animate-in" style={{ animationDelay: '0.3s' }}>
            <a href="/auth/invite" className="btn btn-primary btn-lg">
              <Bot size={20} />
              Add to Discord
              <ArrowRight size={18} />
            </a>
            <a href="/auth/login" className="btn btn-secondary btn-lg">
              <Globe size={20} />
              Open Dashboard
            </a>
          </div>
          <div className="hero-stats animate-in" style={{ animationDelay: '0.4s' }}>
            {STATS.map((s, i) => (
              <div className="hero-stat" key={i}>
                <span className="hero-stat-value">{s.value}</span>
                <span className="hero-stat-label">{s.label}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="hero-preview animate-in" style={{ animationDelay: '0.5s' }}>
          <div className="preview-window glass">
            <div className="preview-topbar">
              <div className="preview-dots">
                <span /><span /><span />
              </div>
              <span className="preview-url">moderations.app/dashboard</span>
            </div>
            <div className="preview-body">
              <div className="preview-sidebar">
                <div className="preview-sidebar-item active"><Shield size={14} /> Overview</div>
                <div className="preview-sidebar-item"><Zap size={14} /> Auto Mod</div>
                <div className="preview-sidebar-item"><Brain size={14} /> AI Mod</div>
                <div className="preview-sidebar-item"><Eye size={14} /> Logging</div>
                <div className="preview-sidebar-item"><Ticket size={14} /> Tickets</div>
                <div className="preview-sidebar-item"><Gavel size={14} /> Cases</div>
              </div>
              <div className="preview-main">
                <div className="preview-header-row">
                  <div className="preview-h">Server Overview</div>
                  <div className="badge badge-success">Online</div>
                </div>
                <div className="preview-grid">
                  <div className="preview-stat-card">
                    <div className="preview-stat-icon" style={{ background: 'rgba(108,92,231,0.15)', color: '#a29bfe' }}><Users size={18} /></div>
                    <div>
                      <div className="preview-stat-num">12,847</div>
                      <div className="preview-stat-lbl">Members</div>
                    </div>
                  </div>
                  <div className="preview-stat-card">
                    <div className="preview-stat-icon" style={{ background: 'rgba(0,214,143,0.15)', color: '#00d68f' }}><ShieldCheck size={18} /></div>
                    <div>
                      <div className="preview-stat-num">1,204</div>
                      <div className="preview-stat-lbl">Actions Today</div>
                    </div>
                  </div>
                  <div className="preview-stat-card">
                    <div className="preview-stat-icon" style={{ background: 'rgba(255,184,0,0.15)', color: '#ffb800' }}><Gavel size={18} /></div>
                    <div>
                      <div className="preview-stat-num">89</div>
                      <div className="preview-stat-lbl">Active Cases</div>
                    </div>
                  </div>
                </div>
                <div className="preview-activity">
                  <div className="preview-activity-row">
                    <span className="preview-dot green" />
                    <span>Auto Mod blocked spam message</span>
                    <span className="preview-time">2m ago</span>
                  </div>
                  <div className="preview-activity-row">
                    <span className="preview-dot yellow" />
                    <span>AI flagged suspicious account</span>
                    <span className="preview-time">5m ago</span>
                  </div>
                  <div className="preview-activity-row">
                    <span className="preview-dot blue" />
                    <span>Ticket #204 resolved by staff</span>
                    <span className="preview-time">12m ago</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section className="features" id="features">
        <div className="container">
          <div className="section-header">
            <span className="section-badge">
              <Zap size={14} />
              Features
            </span>
            <h2 className="section-title">
              Everything you need to
              <span className="gradient-text"> protect your server</span>
            </h2>
            <p className="section-subtitle">
              ModBot combines advanced auto-moderation, AI analysis, and a powerful dashboard
              to give you complete control over your Discord server.
            </p>
          </div>
          <div className="features-grid" id="modules">
            {FEATURES.map((f, i) => (
              <div className="feature-card card" key={i} style={{ animationDelay: `${i * 0.05}s` }}>
                <div className="feature-icon" style={{ background: `${f.color}15`, color: f.color }}>
                  <f.icon size={24} />
                </div>
                <h3 className="feature-title">{f.title}</h3>
                <p className="feature-desc">{f.desc}</p>
                <div className="feature-arrow">
                  <ChevronRight size={16} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Stats Banner ── */}
      <section className="stats-section" id="stats">
        <div className="stats-bg" />
        <div className="container">
          <div className="stats-grid">
            <div className="stats-info">
              <h2 className="stats-title">
                Built for <span className="gradient-text">scale</span>
              </h2>
              <p className="stats-desc">
                ModBot is engineered for performance. Real-time event processing,
                PostgreSQL-backed persistence, Redis caching, and zero-downtime deployments.
              </p>
              <div className="stats-checks">
                <div className="stats-check"><CheckCircle2 size={18} /> Real-time event processing</div>
                <div className="stats-check"><CheckCircle2 size={18} /> PostgreSQL + Redis backed</div>
                <div className="stats-check"><CheckCircle2 size={18} /> Per-server configuration</div>
                <div className="stats-check"><CheckCircle2 size={18} /> Role-based access control</div>
              </div>
            </div>
            <div className="stats-cards">
              {STATS.map((s, i) => (
                <div className="stat-card glass" key={i}>
                  <div className="stat-value gradient-text">{s.value}</div>
                  <div className="stat-label">{s.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="cta">
        <div className="cta-glow" />
        <div className="container cta-content">
          <h2 className="cta-title">
            Ready to secure your server?
          </h2>
          <p className="cta-subtitle">
            Join thousands of server owners who trust ModBot. Set up takes less than 60 seconds.
          </p>
          <div className="cta-actions">
            <a href="/auth/invite" className="btn btn-primary btn-lg">
              <Bot size={20} />
              Add ModBot to Discord
              <ArrowRight size={18} />
            </a>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="footer">
        <div className="container footer-inner">
          <div className="footer-brand">
            <div className="nav-brand">
              <div className="nav-logo">
                <Shield size={20} />
              </div>
              <span className="nav-name">ModBot</span>
            </div>
            <p className="footer-tagline">Advanced Discord moderation, simplified.</p>
          </div>
          <div className="footer-links">
            <div className="footer-col">
              <h4>Product</h4>
              <a href="#features">Features</a>
              <a href="/dashboard">Dashboard</a>
              <a href="#stats">Status</a>
            </div>
            <div className="footer-col">
              <h4>Resources</h4>
              <a href="#">Documentation</a>
              <a href="#">Commands</a>
              <a href="#">Changelog</a>
            </div>
            <div className="footer-col">
              <h4>Community</h4>
              <a href="https://discord.gg/modbot" target="_blank" rel="noopener">Discord</a>
              <a href="#">GitHub</a>
              <a href="#">Twitter</a>
            </div>
          </div>
          <div className="footer-bottom">
            <span>&copy; {new Date().getFullYear()} ModBot. All rights reserved.</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
