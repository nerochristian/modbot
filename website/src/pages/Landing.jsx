import { Link } from 'react-router-dom'
import {
  Activity,
  ArrowRight,
  Bell,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  Crown,
  Gauge,
  Gift,
  Globe2,
  Layers3,
  Lock,
  MessageSquareText,
  Mic2,
  PanelLeft,
  Puzzle,
  Search,
  Settings,
  Shield,
  Sparkles,
  Ticket,
  UserRoundCheck,
  Wand2,
  Zap,
} from 'lucide-react'
import './Landing.css'

const TOP_FEATURES = [
  {
    icon: Zap,
    title: 'Blazing Fast',
    text: 'Instant moderation actions, synced settings, and low-latency responses when your staff needs them.',
  },
  {
    icon: Shield,
    title: 'Secure',
    text: 'Role-aware controls, audit trails, anti-raid tools, and clean permission boundaries for every server.',
  },
  {
    icon: Puzzle,
    title: 'Fully Featured',
    text: 'Moderation, tickets, logging, AI review, automations, and dashboards in one connected system.',
  },
  {
    icon: Settings,
    title: 'Customizable',
    text: 'Tune modules per server with focused setup screens instead of memorizing long command chains.',
  },
]

const PLUGIN_GROUPS = [
  {
    eyebrow: 'Server Management',
    title: 'Keep your community organized from day one.',
    text: 'Welcome flows, roles, activity, and member context are easy to review without leaving the dashboard.',
    accent: '#2586ff',
    items: [
      { icon: UserRoundCheck, title: 'User Management', text: 'Track members, staff notes, cases, and activity in one clean profile.' },
      { icon: Mic2, title: 'Voice Online', text: 'Display live voice activity and keep server participation visible.' },
      { icon: Sparkles, title: 'Levels', text: 'Reward engagement with configurable XP, ranks, and leaderboard views.' },
      { icon: MessageSquareText, title: 'Welcome & Goodbye', text: 'Send polished join and leave messages with server-specific branding.' },
    ],
  },
  {
    eyebrow: 'Moderation & Security',
    title: 'Give staff the tools to act quickly and clearly.',
    text: 'Every action can be reviewed with context, evidence, and the exact module that handled it.',
    accent: '#00a6d6',
    items: [
      { icon: Shield, title: 'Moderation', text: 'Ban, mute, warn, note, and review cases with complete history.' },
      { icon: Bell, title: 'Logs', text: 'Track deleted messages, joins, role edits, voice moves, and staff actions.' },
      { icon: Lock, title: 'Protection', text: 'Anti-raid rules, lockdown tools, account-age gates, and recovery controls.' },
      { icon: Ticket, title: 'Tickets', text: 'Private support channels with claims, transcripts, and staff routing.' },
    ],
  },
  {
    eyebrow: 'Utility & Automation',
    title: 'Automate the repetitive work your team keeps doing.',
    text: 'Create dependable workflows for routine events, responses, roles, and server maintenance.',
    accent: '#4f7cff',
    items: [
      { icon: Wand2, title: 'Auto Responder', text: 'Reply to keywords and common questions with controlled automated messages.' },
      { icon: Layers3, title: 'Backup', text: 'Preserve server settings and recover faster when something changes.' },
      { icon: Gift, title: 'Giveaways', text: 'Run giveaways with simple entry rules and clear winner selection.' },
      { icon: ClipboardList, title: 'Reports', text: 'Route member reports to moderators with the context needed to decide.' },
    ],
  },
]

const STATS = [
  ['12k+', 'servers managed'],
  ['2.1M+', 'actions logged'],
  ['99.9%', 'service uptime'],
  ['24/7', 'automated coverage'],
]

const ACTIVITY = [
  ['Protected', 'Invite spam blocked in #general', 'now'],
  ['Ticket', 'Support ticket claimed by Ava', '22s'],
  ['Case', 'Warning added for repeated caps', '1m'],
  ['Log', 'Role permissions changed by Admin', '4m'],
]

export default function Landing() {
  return (
    <div className="lp">
      <div className="lp-sky" aria-hidden="true" />

      <nav className="lp-nav" aria-label="Primary navigation">
        <div className="lp-nav-inner">
          <Link to="/" className="lp-logo" aria-label="Orion Protection home">
            <img src="/orion-protection.svg" alt="" />
            <span>Orion</span>
          </Link>

          <div className="lp-nav-links">
            <a href="#plugins">Plugins</a>
            <a href="#security">Protection</a>
            <a href="#automation">Automation</a>
            <a href="/dashboard">Dashboard</a>
          </div>

          <div className="lp-nav-actions">
            <button className="lp-language" type="button" aria-label="Language selector">
              <Globe2 size={16} />
              English
              <ChevronDown size={15} />
            </button>
            <a className="lp-login" href="/auth/login">Login</a>
            <a className="lp-primary" href="/auth/invite">
              Invite Bot
              <ArrowRight size={17} />
            </a>
          </div>
        </div>
      </nav>

      <main>
        <section className="lp-hero">
          <div className="lp-hero-copy">
            <span className="lp-pill">
              <Sparkles size={16} />
              All-in-one Discord moderation
            </span>
            <h1>Your Discord control center starts in the clouds.</h1>
            <p>
              Manage moderation, protection, tickets, logs, automations, and staff workflows from one bright,
              fast dashboard built for modern communities.
            </p>

            <div className="lp-hero-actions">
              <a className="lp-primary lp-primary-lg" href="/auth/invite">
                <Bot size={20} />
                Invite Bot
              </a>
              <a className="lp-secondary lp-secondary-lg" href="#plugins">
                Explore More
                <ChevronRight size={18} />
              </a>
            </div>

            <div className="lp-hero-checks" aria-label="Highlights">
              <span><CheckCircle2 size={16} />Free to start</span>
              <span><CheckCircle2 size={16} />Server dashboards</span>
              <span><CheckCircle2 size={16} />Role-safe controls</span>
            </div>
          </div>

          <div className="lp-hero-art" aria-label="Dashboard preview">
            <div className="lp-dashboard">
              <aside className="lp-dash-rail">
                <span className="lp-rail-logo"><Shield size={20} /></span>
                {[PanelLeft, Ticket, Bell, Settings].map((Icon, index) => (
                  <span className={index === 0 ? 'active' : ''} key={index}>
                    <Icon size={18} />
                  </span>
                ))}
              </aside>

              <div className="lp-dash-main">
                <header className="lp-dash-header">
                  <div>
                    <b>Overview</b>
                    <span>Orion Support</span>
                  </div>
                  <div className="lp-search">
                    <Search size={15} />
                    Search logs
                  </div>
                </header>

                <section className="lp-chart-row">
                  {[
                    ['Joins', '184', '+12%', '#08b981'],
                    ['Messages', '9.4k', '+8%', '#2586ff'],
                    ['Tickets', '17', '-3', '#f59e0b'],
                  ].map(([label, value, delta, color]) => (
                    <article className="lp-mini-card" style={{ '--chart': color }} key={label}>
                      <span>{label}</span>
                      <b>{value}</b>
                      <em>{delta} today</em>
                      <i />
                    </article>
                  ))}
                </section>

                <section className="lp-plugin-preview">
                  <div className="lp-preview-head">
                    <span><Puzzle size={16} /> Plugins</span>
                    <strong>6 enabled</strong>
                  </div>
                  <div className="lp-preview-grid">
                    {[
                      ['AutoMod', Shield],
                      ['Tickets', Ticket],
                      ['Logs', Bell],
                      ['AI Review', Sparkles],
                    ].map(([label, Icon]) => (
                      <div className="lp-preview-tile" key={label}>
                        <Icon size={18} />
                        <span>{label}</span>
                      </div>
                    ))}
                  </div>
                </section>

                <section className="lp-activity">
                  <div className="lp-preview-head">
                    <span><Activity size={16} /> Live activity</span>
                    <strong>Online</strong>
                  </div>
                  {ACTIVITY.map(([type, text, time]) => (
                    <div className="lp-activity-row" key={text}>
                      <b>{type}</b>
                      <span>{text}</span>
                      <time>{time}</time>
                    </div>
                  ))}
                </section>
              </div>
            </div>

            <div className="lp-float-card lp-float-top">
              <Crown size={18} />
              <div>
                <b>Protection Active</b>
                <span>Anti-raid watching</span>
              </div>
            </div>
            <div className="lp-float-card lp-float-bottom">
              <Gauge size={18} />
              <div>
                <b>128 actions today</b>
                <span>All logged cleanly</span>
              </div>
            </div>
          </div>
        </section>

        <section className="lp-fast-grid" aria-label="Product strengths">
          {TOP_FEATURES.map(({ icon: Icon, title, text }) => (
            <article className="lp-fast-card" key={title}>
              <Icon size={24} />
              <h2>{title}</h2>
              <p>{text}</p>
            </article>
          ))}
        </section>

        <section className="lp-stats" aria-label="Platform stats">
          {STATS.map(([value, label]) => (
            <div key={label}>
              <strong>{value}</strong>
              <span>{label}</span>
            </div>
          ))}
        </section>

        <section className="lp-section lp-centered" id="plugins">
          <span className="lp-pill">Plugins for every server</span>
          <h2>Pick the tools that match your community.</h2>
          <p>
            Start with a clean setup, enable only the modules you need, and keep expanding as your server grows.
          </p>
        </section>

        {PLUGIN_GROUPS.map((group, index) => (
          <section
            className="lp-plugin-band"
            id={index === 1 ? 'security' : index === 2 ? 'automation' : undefined}
            style={{ '--accent': group.accent }}
            key={group.eyebrow}
          >
            <div className="lp-band-copy">
              <span>{group.eyebrow}</span>
              <h2>{group.title}</h2>
              <p>{group.text}</p>
            </div>
            <div className="lp-plugin-grid">
              {group.items.map(({ icon: Icon, title, text }) => (
                <article className="lp-plugin-card" key={title}>
                  <div>
                    <Icon size={22} />
                  </div>
                  <h3>{title}</h3>
                  <p>{text}</p>
                  <a href="/auth/login">
                    View
                    <ChevronRight size={15} />
                  </a>
                </article>
              ))}
            </div>
          </section>
        ))}

        <section className="lp-cta">
          <div>
            <span className="lp-pill">Ready for a great experience?</span>
            <h2>Get started now.</h2>
            <p>Connect Orion to your server and manage your community with a dashboard that feels clear from the first click.</p>
            <a className="lp-primary lp-primary-lg" href="/auth/invite">
              Invite Bot
              <ArrowRight size={18} />
            </a>
          </div>
        </section>
      </main>

      <footer className="lp-footer">
        <div className="lp-footer-brand">
          <Link to="/" className="lp-logo">
            <img src="/orion-protection.svg" alt="" />
            <span>Orion</span>
          </Link>
          <p>Your all-in-one server companion for moderation, tickets, logging, and protection.</p>
        </div>

        <div>
          <h2>Contact Us</h2>
          <a href="/auth/invite">Discord</a>
        </div>
        <div>
          <h2>Pages</h2>
          <a href="/dashboard">Dashboard</a>
          <a href="#plugins">Plugins</a>
          <a href="#security">Protection</a>
        </div>
        <div>
          <h2>Legal</h2>
          <a href="/">Terms of service</a>
          <a href="/">Privacy policy</a>
          <a href="/">Refund policy</a>
        </div>
      </footer>
    </div>
  )
}
