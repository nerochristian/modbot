import React, { useState } from 'react'
import {
  Shield, MessageSquare, Gavel, Users, ShieldAlert,
  Calendar, Zap, Bell, CheckCircle2, XCircle, TrendingUp,
  ChevronDown, MoreHorizontal, AlertTriangle, Crown, Search,
  Filter, Play, Pause, Download, Settings, Server, Key,
  Lock, ArrowRight, Activity, Clock, Terminal, Box, Globe, RotateCcw
} from 'lucide-react'

// --- Reusable SVG Map ---
const LiveThreatMap = () => (
  <div className="vtx-threat-map">
    <div className="vtx-map-node node-1"></div>
    <div className="vtx-map-node node-2" style={{background:'var(--warning)', boxShadow:'0 0 12px var(--warning)'}}></div>
    <div className="vtx-map-node node-3"></div>
    <div className="vtx-map-node node-4" style={{background:'var(--error)', boxShadow:'0 0 12px var(--error)'}}></div>
    <div className="vtx-map-node node-5"></div>
  </div>
)

// --- Command Center ---
export function CommandCenter() {
  return (
    <div className="vtx-overview">
      <div className="vtx-page-header">
        <div>
          <h1 className="vtx-page-title">Command Center</h1>
          <p className="vtx-page-subtitle">Real-time overview of your server's security and activity.</p>
        </div>
        <div className="vtx-header-actions">
          <button className="btn btn-secondary btn-sm"><AlertTriangle size={14} color="var(--error)"/> Emergency Lockdown</button>
        </div>
      </div>

      <div className="vtx-dashboard-grid">
        <div className="vtx-bento-card col-span-2 vtx-map-card">
          <div className="vtx-bc-header">
            <h3>Live Threat Map</h3>
            <div className="vtx-map-legend">
              <span></span> Clean &nbsp;
              <span></span> Suspicious &nbsp;
              <span></span> Blocked
            </div>
          </div>
          <LiveThreatMap />
        </div>

        <div className="vtx-bento-card">
          <div className="vtx-bc-header">
            <h3>System Overview</h3>
          </div>
          <div className="vtx-ring-summary">
            <div className="vtx-ring">
              <span>98%</span>
              <small>Health</small>
            </div>
            <div className="vtx-ring-list">
              <div><span style={{background:'var(--success)'}}></span> AutoMod <strong>Active</strong></div>
              <div><span style={{background:'var(--success)'}}></span> Anti-Raid <strong>Active</strong></div>
              <div><span style={{background:'var(--warning)'}}></span> Verification <strong>Elevated</strong></div>
            </div>
          </div>
        </div>

        <div className="vtx-bento-card">
          <div className="vtx-bc-header">
            <h3>Quick Actions</h3>
          </div>
          <div className="vtx-action-grid">
            <div className="vtx-action-button"><Search size={16}/><span>Lookup</span></div>
            <div className="vtx-action-button"><Lock size={16}/><span>Lockdown</span></div>
            <div className="vtx-action-button"><ShieldAlert size={16}/><span>Anti-Raid</span></div>
            <div className="vtx-action-button"><MessageSquare size={16}/><span>Clear Chat</span></div>
            <div className="vtx-action-button"><Users size={16}/><span>Prune</span></div>
            <div className="vtx-action-button"><Settings size={16}/><span>Config</span></div>
          </div>
        </div>

        <div className="vtx-bento-card col-span-2">
          <div className="vtx-bc-header">
            <h3>Activity Timeline</h3>
            <span className="vtx-live-dot">Live</span>
          </div>
          <div className="vtx-event-stream">
            <div className="vtx-event-row">
              <span className="vtx-event-time">12:45:02</span>
              <div className="vtx-event-icon" style={{background:'var(--error-bg)', color:'var(--error)'}}><Shield size={14}/></div>
              <div className="vtx-event-copy"><strong>Raid Attempt Blocked</strong><small>Blocked 45 suspicious joins in 30 seconds</small></div>
            </div>
            <div className="vtx-event-row">
              <span className="vtx-event-time">12:44:15</span>
              <div className="vtx-event-icon" style={{background:'var(--warning-bg)', color:'var(--warning)'}}><MessageSquare size={14}/></div>
              <div className="vtx-event-copy"><strong>Spam Filtered</strong><small>Deleted mass mentions by @User123</small></div>
            </div>
            <div className="vtx-event-row">
              <span className="vtx-event-time">12:41:09</span>
              <div className="vtx-event-icon" style={{background:'var(--info-bg)', color:'var(--info)'}}><Users size={14}/></div>
              <div className="vtx-event-copy"><strong>New Member Verified</strong><small>@NewGuy passed captchas</small></div>
            </div>
          </div>
        </div>

        <div className="vtx-bento-card col-span-2">
          <div className="vtx-bc-header">
            <h3>Member Activity Heatmap</h3>
            <button className="btn-ghost btn-xs">24h</button>
          </div>
          <div className="vtx-heatmap">
            {Array.from({length: 48}).map((_, i) => (
              <span key={i} style={{opacity: Math.random() * 0.8 + 0.2}}></span>
            ))}
          </div>
          <div style={{display:'flex', justifyContent:'space-between', fontSize:'0.65rem', color:'var(--text-muted)', marginTop:'8px'}}>
            <span>00:00</span><span>12:00</span><span>23:59</span>
          </div>
        </div>
      </div>
    </div>
  )
}

// --- Events Dashboard ---
export function EventsDashboard() {
  return (
    <div className="vtx-overview">
      <div className="vtx-page-header">
        <div>
          <h1 className="vtx-page-title">Live Events</h1>
          <p className="vtx-page-subtitle">Real-time stream of all server activity.</p>
        </div>
        <div className="vtx-header-actions">
          <button className="btn btn-secondary btn-sm"><Filter size={14}/> Filter</button>
          <button className="btn btn-primary btn-sm"><Pause size={14}/> Pause Stream</button>
        </div>
      </div>

      <div className="vtx-stats-row">
        <div className="vtx-stat-card">
          <div className="vtx-sc-top"><span className="vtx-sc-lbl">Events/min</span><div className="vtx-sc-icon" style={{background:'var(--info-bg)',color:'var(--info)'}}><Activity size={18}/></div></div>
          <div className="vtx-sc-val">124</div>
        </div>
        <div className="vtx-stat-card">
          <div className="vtx-sc-top"><span className="vtx-sc-lbl">Threats/min</span><div className="vtx-sc-icon" style={{background:'var(--error-bg)',color:'var(--error)'}}><ShieldAlert size={18}/></div></div>
          <div className="vtx-sc-val">12</div>
        </div>
        <div className="vtx-stat-card">
          <div className="vtx-sc-top"><span className="vtx-sc-lbl">Joins/min</span><div className="vtx-sc-icon" style={{background:'var(--success-bg)',color:'var(--success)'}}><Users size={18}/></div></div>
          <div className="vtx-sc-val">45</div>
        </div>
      </div>

      <div className="vtx-dashboard-grid">
        <div className="vtx-bento-card col-span-3">
          <div className="vtx-bc-header">
            <h3>Event Stream</h3>
            <span className="vtx-live-dot">Streaming</span>
          </div>
          <div className="vtx-tabs">
            <span className="active">All Events</span>
            <span>Security</span>
            <span>Messages</span>
            <span>Members</span>
          </div>
          <div className="vtx-event-stream" style={{height:'400px', overflowY:'auto'}}>
            {Array.from({length: 15}).map((_, i) => (
              <div className="vtx-event-row" key={i}>
                <span className="vtx-event-time">14:2{i}:{10+i}</span>
                <div className="vtx-event-icon" style={{background:'var(--bg-elevated)', color:'var(--text-secondary)'}}><Terminal size={14}/></div>
                <div className="vtx-event-copy"><strong>User Updated Profile</strong><small>@User{i} changed their avatar</small></div>
                <span className="vtx-severity" style={{color:'var(--text-muted)', borderColor:'var(--border)'}}>INFO</span>
              </div>
            ))}
          </div>
        </div>

        <div className="vtx-bento-card">
          <div className="vtx-bc-header"><h3>Recent Joins</h3></div>
          <div className="vtx-compact-list">
            <div style={{color:'var(--error)'}}><div className="vtx-avatar-dot" data-danger="true">S</div><strong>@SpammerBot</strong><small>1m</small></div>
            <div><div className="vtx-avatar-dot">N</div><strong>@NewUser</strong><small>4m</small></div>
            <div><div className="vtx-avatar-dot">G</div><strong>@GamerPro</strong><small>12m</small></div>
            <div><div className="vtx-avatar-dot">A</div><strong>@Alex</strong><small>15m</small></div>
            <div style={{color:'var(--error)'}}><div className="vtx-avatar-dot" data-danger="true">R</div><strong>@RaidAcc</strong><small>22m</small></div>
          </div>
        </div>
      </div>
    </div>
  )
}

// --- Logs Dashboard ---
export function LogsDashboard() {
  return (
    <div className="vtx-overview log-page">
      <div className="vtx-page-header">
        <div>
          <h1 className="vtx-page-title">Audit Logs</h1>
          <p className="vtx-page-subtitle">Searchable history of all administrative actions.</p>
        </div>
        <div className="vtx-header-actions">
          <button className="btn btn-secondary btn-sm"><Download size={14}/> Export CSV</button>
        </div>
      </div>

      <div className="vtx-bento-card col-span-4" style={{minHeight:'600px'}}>
        <div className="vtx-log-toolbar">
          <span><Search size={14}/> Search by user, action, or ID...</span>
          <button><Filter size={14}/> Type: All</button>
          <button><Filter size={14}/> Mod: All</button>
          <button><Calendar size={14}/> Date Range</button>
        </div>

        <div className="vtx-log-table">
          <div style={{borderBottom:'1px solid var(--border)', paddingBottom:'8px', marginBottom:'8px'}}>
            <em>TIME</em><em>ACTION</em><em>DETAILS</em><em>MODERATOR</em><em>TARGET</em>
          </div>
          {Array.from({length: 10}).map((_, i) => (
            <div key={i}>
              <small>Today 14:20</small>
              <strong><span style={{color: i%3===0 ? 'var(--error)' : 'var(--brand-primary)'}}>{i%3===0 ? 'Ban' : 'Warn'}</span></strong>
              <span>Spamming invite links in general chat</span>
              <strong>@ModName</strong>
              <strong>@BadUser{i}</strong>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// --- Anti-Raid Dashboard ---
export function AntiRaidDashboard() {
  return (
    <div className="vtx-overview">
      <div className="vtx-page-header">
        <div>
          <h1 className="vtx-page-title">Anti-Raid Center</h1>
          <p className="vtx-page-subtitle">Configure advanced protections against coordinated attacks.</p>
        </div>
        <div className="vtx-header-actions">
          <button className="btn btn-danger btn-sm"><AlertTriangle size={14}/> Enable Lockdown</button>
        </div>
      </div>

      <div className="vtx-module-hero" style={{'--module-color':'var(--error)'}}>
        <div className="vtx-module-icon"><ShieldAlert size={24}/></div>
        <div>
          <h2>Anti-Raid is Active</h2>
          <p>Protecting against mass joins, spam bots, and coordinated attacks.</p>
        </div>
        <button className="btn btn-secondary btn-sm">Configure Rules</button>
      </div>

      <div className="vtx-dashboard-grid">
        <div className="vtx-bento-card col-span-2">
          <div className="vtx-bc-header"><h3>Join Velocity Matrix</h3></div>
          <div className="vtx-chart-wrapper" style={{height:'180px'}}>
             <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="vtx-chart-svg">
              <polyline points="0,90 20,85 40,95 60,80 80,20 100,10" fill="none" stroke="var(--error)" strokeWidth="2" />
              <polyline points="0,95 20,95 40,95 60,95 80,95 100,95" fill="none" stroke="var(--success)" strokeWidth="1" strokeDasharray="2" />
            </svg>
          </div>
          <div style={{marginTop:'16px', display:'flex', justifyContent:'space-between'}}>
             <span>Current: <strong>45 joins/min</strong></span>
             <span style={{color:'var(--error)'}}>Threshold: <strong>10 joins/min</strong></span>
          </div>
        </div>

        <div className="vtx-bento-card">
          <div className="vtx-bc-header"><h3>Automated Responses</h3></div>
          <div className="vtx-control-list">
            <div>Enable Captcha <div className="mp-toggle on"><div className="mp-toggle-thumb"></div></div></div>
            <div>Require Avatar <div className="mp-toggle on"><div className="mp-toggle-thumb"></div></div></div>
            <div>Account Age &gt; 3d <div className="mp-toggle on"><div className="mp-toggle-thumb"></div></div></div>
            <div>Quarantine Suspicious <div className="mp-toggle"><div className="mp-toggle-thumb"></div></div></div>
            <div>Auto-Ban Known Bots <div className="mp-toggle on"><div className="mp-toggle-thumb"></div></div></div>
          </div>
        </div>

        <div className="vtx-bento-card">
          <div className="vtx-bc-header"><h3>Recent Incidents</h3></div>
          <div className="vtx-incident-card">
             <ShieldAlert size={24}/>
             <div>
               <strong>Raid Blocked</strong>
               <br/><span>Blocked 150 bots in 2m</span>
             </div>
          </div>
          <div className="vtx-metric-list">
            <div><span>Target</span><strong>#general</strong></div>
            <div><span>Source IP</span><strong>Multiple</strong></div>
            <div><span>Action Taken</span><strong style={{color:'var(--error)'}}>Banned</strong></div>
          </div>
        </div>
      </div>
    </div>
  )
}

// --- Warnings Dashboard ---
export function WarningsDashboard() {
  return (
    <div className="vtx-overview">
      <div className="vtx-page-header">
        <div>
          <h1 className="vtx-page-title">Warnings</h1>
          <p className="vtx-page-subtitle">Track and manage user infractions.</p>
        </div>
      </div>
      
      <div className="vtx-dashboard-grid">
         <div className="vtx-bento-card col-span-3">
           <div className="vtx-bc-header"><h3>Warning History</h3></div>
           <div className="vtx-log-table">
              <div style={{borderBottom:'1px solid var(--border)', paddingBottom:'8px', marginBottom:'8px'}}>
                <em>DATE</em><em>USER</em><em>REASON</em><em>MODERATOR</em><em>STATUS</em>
              </div>
              {Array.from({length: 8}).map((_, i) => (
                <div key={i}>
                  <small>Oct {15-i}</small>
                  <strong>@RuleBreaker{i}</strong>
                  <span>Spamming</span>
                  <strong>@ModAdmin</strong>
                  <span className="vtx-badge vtx-badge-med">Active</span>
                </div>
              ))}
            </div>
         </div>
         <div className="vtx-bento-card">
           <div className="vtx-bc-header"><h3>Top Offenders</h3></div>
           <div className="vtx-lb-list">
              <div className="vtx-lb-item"><div className="vtx-lb-info"><h4>@User1</h4><p>5 warnings</p></div></div>
              <div className="vtx-lb-item"><div className="vtx-lb-info"><h4>@User2</h4><p>3 warnings</p></div></div>
              <div className="vtx-lb-item"><div className="vtx-lb-info"><h4>@User3</h4><p>3 warnings</p></div></div>
              <div className="vtx-lb-item"><div className="vtx-lb-info"><h4>@User4</h4><p>2 warnings</p></div></div>
           </div>
         </div>
      </div>
    </div>
  )
}

// --- Settings Dashboard ---
export function SettingsDashboard() {
  return (
    <div className="vtx-overview settings-page">
      <div className="vtx-page-header">
        <div>
          <h1 className="vtx-page-title">Settings</h1>
          <p className="vtx-page-subtitle">Configure global dashboard and bot preferences.</p>
        </div>
        <div className="vtx-header-actions">
          <button className="btn btn-primary btn-sm">Save Changes</button>
        </div>
      </div>

      <div className="settings-section">
        <h3>General Configuration</h3>
        <div className="settings-row">
          <label>Command Prefix</label>
          <input type="text" defaultValue="!" />
        </div>
        <div className="settings-row">
          <label>Language</label>
          <select><option>English (US)</option><option>Spanish</option></select>
        </div>
        <div className="settings-row">
          <label>Timezone</label>
          <select><option>UTC</option><option>EST</option></select>
        </div>
      </div>

      <div className="settings-section">
        <h3>Role Mappings</h3>
        <div className="settings-row">
          <label>Admin Role</label>
          <select><option>@Admin</option><option>@Owner</option></select>
        </div>
        <div className="settings-row">
          <label>Moderator Role</label>
          <select><option>@Mod</option><option>@Trial Mod</option></select>
        </div>
        <div className="settings-row">
          <label>Muted Role</label>
          <select><option>@Muted</option><option>Create New</option></select>
        </div>
      </div>
    </div>
  )
}

// --- Premium Dashboard ---
export function PremiumDashboard() {
  return (
    <div className="vtx-overview">
      <div className="vtx-page-header">
        <div>
          <h1 className="vtx-page-title">Subscription</h1>
          <p className="vtx-page-subtitle">Manage your Vortex Premium plan and billing.</p>
        </div>
      </div>

      <div className="vtx-premium-hero">
        <div className="vtx-premium-mark"><Crown size={28}/></div>
        <div>
          <h2>Vortex Pro Active</h2>
          <p>You are currently on the Pro plan, billed monthly. Next billing date: Nov 15, 2026.</p>
          <div className="vtx-premium-grid">
            <div><CheckCircle2 size={16}/> Priority AutoMod Routing</div>
            <div><CheckCircle2 size={16}/> 1 Year Log Retention</div>
            <div><CheckCircle2 size={16}/> Advanced Analytics</div>
            <div><CheckCircle2 size={16}/> White-label Bot Option</div>
          </div>
        </div>
        <div style={{marginLeft:'auto', display:'flex', flexDirection:'column', gap:'12px'}}>
           <button className="btn btn-primary">Manage Billing</button>
           <button className="btn btn-secondary">View Invoices</button>
        </div>
      </div>
    </div>
  )
}

// Export a fallback so existing routes don't crash if they try to render an unimplemented view
export function FallbackView({ title }) {
  return (
    <div className="vtx-overview">
       <div className="vtx-page-header">
         <h1 className="vtx-page-title">{title || 'Dashboard View'}</h1>
       </div>
       <div className="empty-state">
         <Box size={48}/>
         <h3>Under Construction</h3>
         <p>This view is currently being built to match the high-fidelity mockups.</p>
       </div>
    </div>
  )
}

export const ModerationDashboard = () => <FallbackView title="Moderation Panel" />
export const MembersDashboard = () => <FallbackView title="Member Management" />
export const AppealsDashboard = () => <FallbackView title="Appeals System" />
export const BackupDashboard = () => <FallbackView title="Server Backups" />
export const IntegrationsDashboard = () => <FallbackView title="Integrations" />

