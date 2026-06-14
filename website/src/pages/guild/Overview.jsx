import { useState, useEffect } from 'react'
import {
  Shield, MessageSquare, Gavel, Users, ShieldCheck,
  Calendar, Zap, Bell, CheckCircle2, XCircle, TrendingUp,
  ChevronDown, MoreHorizontal, AlertTriangle, Crown
} from 'lucide-react'
import { useGuild } from './GuildContext'
import { api } from '../../api'

// --- Custom SVG Components ---

const LineChart = ({ data, color, height = 120, labelX = [], yMax = 100 }) => {
  const points = data.map((val, i) => {
    const x = (i / (data.length - 1)) * 100
    const y = 100 - (val / yMax) * 100
    return `${x},${y}`
  }).join(' ')

  return (
    <div className="vtx-chart-wrapper" style={{ height }}>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="vtx-chart-svg">
        <defs>
          <linearGradient id={`grad-${color}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.3" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
          <filter id={`glow-${color}`} x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>
        
        {/* Grid lines */}
        <line x1="0" y1="25" x2="100" y2="25" stroke="var(--border-subtle)" strokeWidth="0.5" />
        <line x1="0" y1="50" x2="100" y2="50" stroke="var(--border-subtle)" strokeWidth="0.5" />
        <line x1="0" y1="75" x2="100" y2="75" stroke="var(--border-subtle)" strokeWidth="0.5" />
        
        {/* Area fill */}
        <polygon points={`0,100 ${points} 100,100`} fill={`url(#grad-${color})`} />
        
        {/* Line */}
        <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" filter={`url(#glow-${color})`} />
        
        {/* Points */}
        {data.map((val, i) => {
          const x = (i / (data.length - 1)) * 100
          const y = 100 - (val / yMax) * 100
          return <circle key={i} cx={x} cy={y} r="1.5" fill={color} />
        })}
      </svg>
      <div className="vtx-chart-labels-x">
        {labelX.map((lbl, i) => <span key={i}>{lbl}</span>)}
      </div>
    </div>
  )
}

const DonutChart = ({ total, segments }) => {
  let currentOffset = 0;
  return (
    <div className="vtx-donut-wrapper">
      <svg viewBox="0 0 100 100" className="vtx-donut-svg">
        {segments.map((seg, i) => {
          const dashArray = `${seg.pct} ${100 - seg.pct}`;
          const strokeDashoffset = -currentOffset;
          currentOffset += seg.pct;
          return (
            <circle
              key={i} cx="50" cy="50" r="40" fill="none"
              stroke={seg.color} strokeWidth="15"
              strokeDasharray={dashArray} strokeDashoffset={strokeDashoffset}
            />
          )
        })}
      </svg>
      <div className="vtx-donut-center">
        <span className="vtx-donut-total">{total}</span>
        <span className="vtx-donut-lbl">Total Actions</span>
      </div>
    </div>
  )
}

const ProgressBar = ({ label, pct, color, rightText }) => (
  <div className="vtx-pb">
    <div className="vtx-pb-header">
      <span className="vtx-pb-lbl">{label}</span>
      {rightText && <span className="vtx-pb-val">{rightText}</span>}
    </div>
    <div className="vtx-pb-track">
      <div className="vtx-pb-fill" style={{ width: `${pct}%`, background: color }}></div>
    </div>
  </div>
)

// --- Main Component ---

export default function Overview() {
  const { guild, guildId } = useGuild()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getGuildStats(guildId).then(setStats).catch(() => {}).finally(() => setLoading(false))
  }, [guildId])

  return (
    <div className="vtx-overview">
      {/* Page Header */}
      <div className="vtx-page-header">
        <div>
          <h1 className="vtx-page-title">Overview</h1>
          <p className="vtx-page-subtitle">Monitor your server's security, activity and moderation in real time.</p>
        </div>
        <div className="vtx-header-actions">
          <button className="btn btn-secondary btn-sm"><Zap size={14}/> Quick Actions</button>
          <button className="btn btn-secondary btn-sm"><Calendar size={14}/> May 17 - May 24</button>
          <button className="btn btn-primary btn-sm">+ Add Widget</button>
        </div>
      </div>

      {/* Top Stats */}
      <div className="vtx-stats-row">
        <div className="vtx-stat-card">
          <div className="vtx-sc-top">
            <span className="vtx-sc-lbl">Threats Blocked</span>
            <div className="vtx-sc-icon" style={{background: 'var(--success-bg)', color: 'var(--success)'}}><Shield size={18}/></div>
          </div>
          <div className="vtx-sc-val">247</div>
          <div className="vtx-sc-trend vtx-trend-up">▲ 18.6% <span className="vtx-trend-lbl">vs last 7 days</span></div>
        </div>
        <div className="vtx-stat-card">
          <div className="vtx-sc-top">
            <span className="vtx-sc-lbl">Messages Filtered</span>
            <div className="vtx-sc-icon" style={{background: 'var(--info-bg)', color: 'var(--info)'}}><MessageSquare size={18}/></div>
          </div>
          <div className="vtx-sc-val">1,842</div>
          <div className="vtx-sc-trend vtx-trend-up">▲ 23.7% <span className="vtx-trend-lbl">vs last 7 days</span></div>
        </div>
        <div className="vtx-stat-card">
          <div className="vtx-sc-top">
            <span className="vtx-sc-lbl">Actions Taken</span>
            <div className="vtx-sc-icon" style={{background: 'var(--warning-bg)', color: 'var(--warning)'}}><Gavel size={18}/></div>
          </div>
          <div className="vtx-sc-val">392</div>
          <div className="vtx-sc-trend vtx-trend-up">▲ 12.4% <span className="vtx-trend-lbl">vs last 7 days</span></div>
        </div>
        <div className="vtx-stat-card">
          <div className="vtx-sc-top">
            <span className="vtx-sc-lbl">Members Protected</span>
            <div className="vtx-sc-icon" style={{background: 'var(--brand-glow)', color: 'var(--brand-primary)'}}><Users size={18}/></div>
          </div>
          <div className="vtx-sc-val">12,842</div>
          <div className="vtx-sc-trend vtx-trend-up">▲ 15.3% <span className="vtx-trend-lbl">vs last 7 days</span></div>
        </div>
        <div className="vtx-stat-card">
          <div className="vtx-sc-top">
            <span className="vtx-sc-lbl">Uptime</span>
            <div className="vtx-sc-icon" style={{background: 'var(--success-bg)', color: 'var(--success)'}}><ShieldCheck size={18}/></div>
          </div>
          <div className="vtx-sc-val">99.99%</div>
          <div className="vtx-sc-trend vtx-trend-up" style={{color: 'var(--success)'}}>Excellent</div>
        </div>
      </div>

      {/* Bento Grid */}
      <div className="vtx-bento-grid">
        
        {/* Row 2 */}
        <div className="vtx-bento-card col-span-2">
          <div className="vtx-bc-header">
            <h3>Threat Activity</h3>
            <button className="btn-ghost btn-xs">Last 7 Days <ChevronDown size={12}/></button>
          </div>
          <LineChart data={[20,40,20,50,45,60,40,50,30,45,25]} color="var(--brand-primary)" labelX={['May 17', 'May 18', 'May 19', 'May 20', 'May 21', 'May 22', 'May 23', 'May 24']} yMax={80}/>
        </div>

        <div className="vtx-bento-card">
          <div className="vtx-bc-header">
            <h3>Recent Events</h3>
            <span className="vtx-bc-link">View All</span>
          </div>
          <div className="vtx-list">
            <div className="vtx-li">
              <div className="vtx-li-icon" style={{color: 'var(--error)', background: 'var(--error-bg)'}}><Shield size={14}/></div>
              <div className="vtx-li-text"><h4>Raid attempt blocked</h4><p>15 suspicious joins</p></div>
              <div className="vtx-li-time">2m ago</div>
            </div>
            <div className="vtx-li">
              <div className="vtx-li-icon" style={{color: 'var(--warning)', background: 'var(--warning-bg)'}}><Gavel size={14}/></div>
              <div className="vtx-li-text"><h4>Spam messages filtered</h4><p>28 messages removed</p></div>
              <div className="vtx-li-time">5m ago</div>
            </div>
            <div className="vtx-li">
              <div className="vtx-li-icon" style={{color: 'var(--error)', background: 'var(--error-bg)'}}><AlertTriangle size={14}/></div>
              <div className="vtx-li-text"><h4>User quarantined</h4><p>Suspicious account detected</p></div>
              <div className="vtx-li-time">12m ago</div>
            </div>
            <div className="vtx-li">
              <div className="vtx-li-icon" style={{color: 'var(--info)', background: 'var(--info-bg)'}}><AlertTriangle size={14}/></div>
              <div className="vtx-li-text"><h4>Warning issued</h4><p>Spamming in #general</p></div>
              <div className="vtx-li-time">18m ago</div>
            </div>
            <div className="vtx-li">
              <div className="vtx-li-icon" style={{color: 'var(--error)', background: 'var(--error-bg)'}}><Shield size={14}/></div>
              <div className="vtx-li-text"><h4>Link blocked</h4><p>Malicious link detected</p></div>
              <div className="vtx-li-time">25m ago</div>
            </div>
          </div>
        </div>

        <div className="vtx-bento-card">
          <div className="vtx-bc-header">
            <h3>Top Threats</h3>
            <span className="vtx-bc-link">View All</span>
          </div>
          <div className="vtx-pb-list">
            <ProgressBar label="Spam Links" pct={42} color="var(--error)" rightText="42%"/>
            <ProgressBar label="Raid Attempts" pct={28} color="var(--warning)" rightText="28%"/>
            <ProgressBar label="Mass Mentions" pct={15} color="var(--warning)" rightText="15%"/>
            <ProgressBar label="Excessive Caps" pct={8} color="var(--brand-primary)" rightText="8%"/>
            <ProgressBar label="Bad Words" pct={7} color="var(--info)" rightText="7%"/>
          </div>
        </div>

        {/* Row 3 */}
        <div className="vtx-bento-card">
          <div className="vtx-bc-header">
            <h3>AutoMod Overview</h3>
          </div>
          <div className="vtx-donut-container">
            <DonutChart total="892" segments={[
              { pct: 46, color: 'var(--error)' },
              { pct: 24, color: 'var(--warning)' },
              { pct: 14, color: 'var(--success)' },
              { pct: 11, color: 'var(--info)' },
              { pct: 5,  color: 'var(--brand-primary)' }
            ]} />
            <div className="vtx-donut-legend">
              <div className="vtx-dl-item"><span className="vtx-dl-dot" style={{background:'var(--error)'}}></span> Message Deleted <span className="vtx-dl-val">412 (46%)</span></div>
              <div className="vtx-dl-item"><span className="vtx-dl-dot" style={{background:'var(--warning)'}}></span> Link Blocked <span className="vtx-dl-val">213 (24%)</span></div>
              <div className="vtx-dl-item"><span className="vtx-dl-dot" style={{background:'var(--success)'}}></span> Mention Blocked <span className="vtx-dl-val">125 (14%)</span></div>
              <div className="vtx-dl-item"><span className="vtx-dl-dot" style={{background:'var(--info)'}}></span> Word Filtered <span className="vtx-dl-val">98 (11%)</span></div>
              <div className="vtx-dl-item"><span className="vtx-dl-dot" style={{background:'var(--brand-primary)'}}></span> Other <span className="vtx-dl-val">44 (5%)</span></div>
            </div>
          </div>
        </div>

        <div className="vtx-bento-card col-span-2">
          <div className="vtx-bc-header">
            <h3>Member Growth</h3>
            <div className="vtx-bc-stats">Joined <span style={{color:'var(--success)'}}>▲ 1,245</span> &nbsp;&nbsp; Left <span style={{color:'var(--error)'}}>▼ 327</span></div>
          </div>
          <LineChart data={[0,5,10,8,15,12,20,18,25,22,30]} color="#10b981" labelX={['May 17', 'May 19', 'May 21', 'May 23']} yMax={40} height={100}/>
          <div className="vtx-growth-bottom">
            <div><span className="vtx-gb-lbl">Total Members</span><span className="vtx-gb-val">12,842 <span className="vtx-trend-up">▲ 5.2%</span></span></div>
            <div><span className="vtx-gb-lbl">Bots</span><span className="vtx-gb-val">18</span></div>
            <div><span className="vtx-gb-lbl">Humans</span><span className="vtx-gb-val">12,824</span></div>
          </div>
        </div>

        <div className="vtx-bento-card">
          <div className="vtx-bc-header">
            <h3>Active Cases</h3>
            <span className="vtx-bc-link">View All</span>
          </div>
          <div className="vtx-case-list">
            <div className="vtx-case-item">
              <div className="vtx-ci-left"><span className="vtx-ci-id">#4821</span><div className="vtx-ci-text"><h4>Scam Link Spam</h4><p>User: @Scammer</p></div></div>
              <span className="vtx-badge vtx-badge-high">High</span>
            </div>
            <div className="vtx-case-item">
              <div className="vtx-ci-left"><span className="vtx-ci-id">#4820</span><div className="vtx-ci-text"><h4>Raid Attempt</h4><p>User: @Unknown</p></div></div>
              <span className="vtx-badge vtx-badge-med">Medium</span>
            </div>
            <div className="vtx-case-item">
              <div className="vtx-ci-left"><span className="vtx-ci-id">#4819</span><div className="vtx-ci-text"><h4>Harassment</h4><p>User: @ToxicUser</p></div></div>
              <span className="vtx-badge vtx-badge-med">Medium</span>
            </div>
            <div className="vtx-case-item">
              <div className="vtx-ci-left"><span className="vtx-ci-id">#4818</span><div className="vtx-ci-text"><h4>Mass Mentions</h4><p>User: @Annoying</p></div></div>
              <span className="vtx-badge vtx-badge-low">Low</span>
            </div>
            <div className="vtx-case-item">
              <div className="vtx-ci-left"><span className="vtx-ci-id">#4817</span><div className="vtx-ci-text"><h4>Inappropriate Names</h4><p>User: @User123</p></div></div>
              <span className="vtx-badge vtx-badge-low">Low</span>
            </div>
          </div>
        </div>

        {/* Row 4 */}
        <div className="vtx-bento-card">
          <div className="vtx-bc-header">
            <h3>Moderator Leaderboard</h3>
            <span className="vtx-bc-link">View All</span>
          </div>
          <div className="vtx-lb-list">
            <div className="vtx-lb-item">
              <span className="vtx-lb-rank">1</span>
              <div className="vtx-lb-av" style={{background:'#6b21a8'}}></div>
              <div className="vtx-lb-info"><h4>Nova</h4><p>Actions: 247</p></div>
              <div className="vtx-lb-score">
                <div className="vtx-lb-bar"><div style={{width:'100%', background:'var(--brand-primary)'}}></div></div>
                <span>2,487 <small>Points</small></span>
              </div>
            </div>
            <div className="vtx-lb-item">
              <span className="vtx-lb-rank">2</span>
              <div className="vtx-lb-av" style={{background:'#ea580c'}}></div>
              <div className="vtx-lb-info"><h4>Velocity</h4><p>Actions: 182</p></div>
              <div className="vtx-lb-score">
                <div className="vtx-lb-bar"><div style={{width:'75%', background:'var(--brand-primary)', opacity: 0.7}}></div></div>
                <span>1,842 <small>Points</small></span>
              </div>
            </div>
            <div className="vtx-lb-item">
              <span className="vtx-lb-rank">3</span>
              <div className="vtx-lb-av" style={{background:'#0369a1'}}></div>
              <div className="vtx-lb-info"><h4>Stellar</h4><p>Actions: 156</p></div>
              <div className="vtx-lb-score">
                <div className="vtx-lb-bar"><div style={{width:'65%', background:'var(--brand-primary)', opacity: 0.45}}></div></div>
                <span>1,563 <small>Points</small></span>
              </div>
            </div>
          </div>
        </div>

        <div className="vtx-bento-card">
          <div className="vtx-bc-header">
            <h3>Recent Logs</h3>
            <span className="vtx-bc-link">View All</span>
          </div>
          <div className="vtx-logs-list">
            <div className="vtx-log-item">
              <span className="vtx-log-time">15:42</span>
              <MessageSquare size={12} className="vtx-log-icon" />
              <span className="vtx-log-txt">Message deleted in <span className="vtx-log-highlight">#general</span></span>
              <span className="vtx-log-user" style={{color:'var(--error)'}}>@Spammer</span>
            </div>
            <div className="vtx-log-item">
              <span className="vtx-log-time">15:41</span>
              <Users size={12} className="vtx-log-icon" />
              <span className="vtx-log-txt">User banned</span>
              <span className="vtx-log-user" style={{color:'var(--error)'}}>@BadUser</span>
            </div>
            <div className="vtx-log-item">
              <span className="vtx-log-time">15:40</span>
              <Shield size={12} className="vtx-log-icon" />
              <span className="vtx-log-txt">Role added</span>
              <span className="vtx-log-user" style={{color:'var(--success)'}}>@Member</span>
            </div>
            <div className="vtx-log-item">
              <span className="vtx-log-time">15:39</span>
              <AlertTriangle size={12} className="vtx-log-icon" />
              <span className="vtx-log-txt">Channel locked</span>
              <span className="vtx-log-user" style={{color:'var(--warning)'}}>#memes</span>
            </div>
            <div className="vtx-log-item">
              <span className="vtx-log-time">15:38</span>
              <AlertTriangle size={12} className="vtx-log-icon" />
              <span className="vtx-log-txt">Warning issued</span>
              <span className="vtx-log-user" style={{color:'var(--brand-primary)'}}>@Talkative</span>
            </div>
          </div>
        </div>

        <div className="vtx-bento-card">
          <div className="vtx-bc-header">
            <h3>System Status</h3>
          </div>
          <div className="vtx-sys-list">
            <div className="vtx-sys-item">
              <div className="vtx-sys-left"><CheckCircle2 size={14} color="var(--text-muted)"/> <span>Dashboard</span></div>
              <span className="vtx-sys-stat">Operational <div className="vtx-stat-dot"></div></span>
            </div>
            <div className="vtx-sys-item">
              <div className="vtx-sys-left"><CheckCircle2 size={14} color="var(--text-muted)"/> <span>AutoMod</span></div>
              <span className="vtx-sys-stat">Operational <div className="vtx-stat-dot"></div></span>
            </div>
            <div className="vtx-sys-item">
              <div className="vtx-sys-left"><CheckCircle2 size={14} color="var(--text-muted)"/> <span>Anti-Raid</span></div>
              <span className="vtx-sys-stat">Operational <div className="vtx-stat-dot"></div></span>
            </div>
            <div className="vtx-sys-item">
              <div className="vtx-sys-left"><CheckCircle2 size={14} color="var(--text-muted)"/> <span>Logs</span></div>
              <span className="vtx-sys-stat">Operational <div className="vtx-stat-dot"></div></span>
            </div>
            <div className="vtx-sys-item">
              <div className="vtx-sys-left"><CheckCircle2 size={14} color="var(--text-muted)"/> <span>Backup System</span></div>
              <span className="vtx-sys-stat">Operational <div className="vtx-stat-dot"></div></span>
            </div>
          </div>
        </div>

        <div className="vtx-bento-card vtx-premium-card">
          <div className="vtx-prem-header">
            <h3>Upgrade to Premium</h3>
          </div>
          <div className="vtx-prem-list">
            <div className="vtx-prem-item"><CheckCircle2 size={14} color="var(--brand-primary)"/> Advanced Anti-Raid</div>
            <div className="vtx-prem-item"><CheckCircle2 size={14} color="var(--brand-primary)"/> Custom AutoMod Rules</div>
            <div className="vtx-prem-item"><CheckCircle2 size={14} color="var(--brand-primary)"/> Unlimited Server Backups</div>
            <div className="vtx-prem-item"><CheckCircle2 size={14} color="var(--brand-primary)"/> Priority Support</div>
          </div>
          <button className="btn btn-primary vtx-prem-btn">Upgrade Now <Crown size={14}/></button>
          <Crown size={80} className="vtx-prem-bg-icon"/>
        </div>

      </div>
    </div>
  )
}
