import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Shield, Zap, Terminal, Database, Users, Settings, Activity,
  Lock, Eye, AlertTriangle, CheckCircle2, XCircle, Clock,
  ChevronRight, ArrowUpRight, BarChart3, Search, MessageSquare, Menu,
  ShieldAlert, ScrollText, Sun, Moon
} from 'lucide-react'
import { Link } from 'react-router-dom'
import './Landing.css'

/* ── Custom Shield Logo ── */
const VortexLogo = ({ size = 24 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    <path d="M9 10l3 4 3-4" />
  </svg>
)

/* ── Components ────────────────────────────────────────────────── */

const Nav = () => {
  const [theme, setTheme] = useState(() => document.documentElement.getAttribute('data-theme') || 'dark')
  
  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark'
    setTheme(newTheme)
    document.documentElement.setAttribute('data-theme', newTheme)
    localStorage.setItem('theme', newTheme)
  }

  return (
    <nav className="lp-nav">
      <Link to="/" className="lp-logo">
        <div className="lp-logo-icon"><VortexLogo /></div>
        VORTEX <span style={{fontWeight:400, fontSize:'0.8rem', letterSpacing:'1px', opacity:0.6, marginLeft:4}}>MODERATION</span>
      </Link>
      <div className="lp-links">
        <a href="#features">Features</a>
        <a href="#commands">Commands</a>
        <a href="#security">Security</a>
        <a href="#dashboard">Dashboard</a>
        <a href="#docs">Documentation</a>
        <a href="#support">Support</a>
      </div>
      <div className="lp-actions">
        <button onClick={toggleTheme} className="lp-btn-ghost" style={{padding: '10px', display: 'flex', cursor: 'pointer'}} title="Toggle Theme">
          {theme === 'dark' ? <Sun size={16}/> : <Moon size={16}/>}
        </button>
        <a href="/auth/login" className="lp-btn-ghost">View Dashboard</a>
        <a href="/auth/invite" className="lp-btn-primary"><img src="https://assets-global.website-files.com/6257adef93867e50d84d30e2/636e0a6a49cf127bf92de1e2_icon_clyde_blurple_RGB.png" alt="Discord" style={{width:16, filter:'brightness(0) invert(1)'}}/> Add to Discord</a>
      </div>
    </nav>
  )
}

const HeroMockup = () => {
  return (
    <div className="lp-mockup">
      <div className="lp-mockup-disc-sidebar">
        <div className="lp-disc-icon active"><VortexLogo size={28}/></div>
        <div style={{width: 32, height: 2, background: 'rgba(255,255,255,0.1)', margin: '4px 0'}} />
        <div className="lp-disc-icon"><Users size={20} color="#dbdee1"/></div>
        <div className="lp-disc-icon"><Activity size={20} color="#dbdee1"/></div>
        <div className="lp-disc-icon"><Terminal size={20} color="#dbdee1"/></div>
      </div>
      <div className="lp-mockup-disc-nav">
        <div style={{fontWeight: 700, color: 'white', marginBottom: 20, display: 'flex', justifyContent: 'space-between'}}>
          Astral Community <ChevronRight size={16} color="var(--cine-text-muted)"/>
        </div>
        <div style={{fontSize: '0.75rem', fontWeight: 700, color: 'var(--cine-text-muted)', marginBottom: 12}}>SERVER STATS</div>
        <div style={{display:'flex', justifyContent:'space-between', fontSize:'0.85rem', color:'var(--cine-text-dim)', marginBottom:8}}>
          <span>Threat Level</span><span style={{color:'var(--cine-success)', fontWeight:600}}>SECURE</span>
        </div>
        <div style={{display:'flex', justifyContent:'space-between', fontSize:'0.85rem', color:'var(--cine-text-dim)', marginBottom:8}}>
          <span>Members</span><span style={{color:'white'}}>12,842</span>
        </div>
        <div style={{display:'flex', justifyContent:'space-between', fontSize:'0.85rem', color:'var(--cine-text-dim)', marginBottom:8}}>
          <span>Channels</span><span style={{color:'white'}}>156</span>
        </div>
        <div style={{display:'flex', justifyContent:'space-between', fontSize:'0.85rem', color:'var(--cine-text-dim)', marginBottom:24}}>
          <span>Uptime</span><span style={{color:'white'}}>99.99%</span>
        </div>
        <div style={{fontSize: '0.75rem', fontWeight: 700, color: 'var(--cine-text-muted)', marginBottom: 12}}>BOT STATUS</div>
        <div style={{display:'flex', alignItems:'center', gap:8, background:'rgba(255,255,255,0.05)', padding:8, borderRadius:6, marginBottom:20}}>
          <div style={{width:24, height:24, borderRadius:'50%', background:'var(--cine-primary)', display:'flex', alignItems:'center', justifyContent:'center'}}>
             <VortexLogo size={14}/>
          </div>
          <span style={{color:'white', fontWeight:600, fontSize:'0.9rem'}}>Vortex</span>
          <span style={{color:'var(--cine-success)', fontSize:'0.7rem', fontWeight:700, marginLeft:'auto'}}>ONLINE</span>
        </div>
        
        <div style={{display:'flex', flexDirection:'column', gap:4}}>
          <div style={{background:'rgba(124,109,240,0.1)', color:'white', padding:'8px 12px', borderRadius:6, display:'flex', alignItems:'center', gap:8, fontSize:'0.9rem', fontWeight:500}}>
            <Activity size={16} color="var(--cine-primary)"/> Overview
          </div>
          <div style={{color:'var(--cine-text-dim)', padding:'8px 12px', display:'flex', alignItems:'center', gap:8, fontSize:'0.9rem', fontWeight:500}}>
            <Database size={16}/> Events
          </div>
          <div style={{color:'var(--cine-text-dim)', padding:'8px 12px', display:'flex', alignItems:'center', gap:8, fontSize:'0.9rem', fontWeight:500}}>
            <ScrollText size={16}/> Logs
          </div>
          <div style={{color:'var(--cine-text-dim)', padding:'8px 12px', display:'flex', alignItems:'center', gap:8, fontSize:'0.9rem', fontWeight:500}}>
            <Zap size={16}/> AutoMod
          </div>
          <div style={{color:'var(--cine-text-dim)', padding:'8px 12px', display:'flex', alignItems:'center', gap:8, fontSize:'0.9rem', fontWeight:500}}>
            <Shield size={16}/> Anti-Raid
          </div>
          <div style={{color:'var(--cine-text-dim)', padding:'8px 12px', display:'flex', alignItems:'center', gap:8, fontSize:'0.9rem', fontWeight:500}}>
            <Settings size={16}/> Settings
          </div>
        </div>
      </div>
      
      <div className="lp-mockup-dash">
        <div className="lp-dash-header">
          <div style={{display:'flex', alignItems:'center', gap:12}}>
            <div style={{width:32, height:32, background:'rgba(124,109,240,0.1)', borderRadius:8, display:'flex', alignItems:'center', justifyContent:'center', color:'var(--cine-primary)'}}>
              <Activity size={18}/>
            </div>
            <div>
              <div style={{color:'white', fontWeight:600, fontSize:'0.95rem'}}>Live Protection</div>
              <div style={{color:'var(--cine-text-muted)', fontSize:'0.75rem'}}>Real-time server protection and event monitor</div>
            </div>
          </div>
          <div style={{display:'flex', alignItems:'center', gap:8, color:'var(--cine-success)', fontSize:'0.75rem', fontWeight:600}}>
            <span style={{width:6, height:6, borderRadius:'50%', background:'var(--cine-success)', boxShadow:'0 0 8px var(--cine-success)'}}/>
            All Systems Operational
          </div>
        </div>
        <div className="lp-dash-body">
          <div className="lp-dash-center">
            <div className="lp-center-shield">
              <div className="lp-center-shield-bg"/>
              <VortexLogo />
              <div className="lp-shield-text">SERVER PROTECTED</div>
            </div>
            
            <div className="lp-float-panel lp-fp-1">
              <div className="lp-float-icon" style={{background:'rgba(239,68,68,0.1)', color:'var(--cine-danger)'}}><AlertTriangle size={18}/></div>
              <div className="lp-float-text"><h4>RAID DETECTED</h4><p>15 suspicious joins</p></div>
            </div>
            <div className="lp-float-panel lp-fp-2">
              <div className="lp-float-icon" style={{background:'rgba(245,158,11,0.1)', color:'var(--cine-warning)'}}><Lock size={18}/></div>
              <div className="lp-float-text"><h4>USER QUARANTINED</h4><p>Suspicious account</p></div>
            </div>
            <div className="lp-float-panel lp-fp-3" style={{top:'30%', right:'5%'}}>
              <div className="lp-float-icon" style={{background:'rgba(34,211,238,0.1)', color:'var(--cine-cyan)'}}><MessageSquare size={18}/></div>
              <div className="lp-float-text"><h4>WARNING ISSUED</h4><p>User warned</p></div>
            </div>
            <div className="lp-float-panel lp-fp-4" style={{bottom:'35%', right:'2%'}}>
              <div className="lp-float-icon" style={{background:'rgba(124,109,240,0.1)', color:'var(--cine-primary)'}}><Database size={18}/></div>
              <div className="lp-float-text"><h4>CASE CREATED</h4><p>Case #4821 created</p></div>
            </div>
            
            <div style={{position:'absolute', bottom: 24, left: 24, right: 24}}>
              <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-end', marginBottom: 12}}>
                 <span style={{color:'white', fontWeight:600, fontSize:'0.85rem'}}>Recent Events</span>
                 <span style={{color:'var(--cine-text-muted)', fontSize:'0.75rem'}}>View All Events</span>
              </div>
              <div style={{display:'grid', gridTemplateColumns:'minmax(0, 1fr) minmax(0, 1fr)', gap:12}}>
                <div style={{background:'rgba(255,255,255,0.02)', border:'1px solid var(--cine-border)', borderRadius:6, padding:12, display:'flex', alignItems:'center', gap:12, minWidth:0}}>
                  <Shield size={16} color="var(--cine-success)" style={{flexShrink:0}}/>
                  <div style={{overflow:'hidden', minWidth:0}}><div style={{color:'var(--cine-text)', fontSize:'0.75rem', fontWeight:600, whiteSpace:'nowrap', textOverflow:'ellipsis', overflow:'hidden'}}>Raid attempt blocked</div><div style={{color:'var(--cine-text-muted)', fontSize:'0.65rem'}}>15 suspicious joins</div></div>
                </div>
                <div style={{background:'rgba(255,255,255,0.02)', border:'1px solid var(--cine-border)', borderRadius:6, padding:12, display:'flex', alignItems:'center', gap:12, minWidth:0}}>
                  <Zap size={16} color="var(--cine-primary)" style={{flexShrink:0}}/>
                  <div style={{overflow:'hidden', minWidth:0}}><div style={{color:'var(--cine-text)', fontSize:'0.75rem', fontWeight:600, whiteSpace:'nowrap', textOverflow:'ellipsis', overflow:'hidden'}}>Spam messages filtered</div><div style={{color:'var(--cine-text-muted)', fontSize:'0.65rem'}}>28 messages removed</div></div>
                </div>
              </div>
            </div>
          </div>
          
          <div className="lp-dash-right">
            <div style={{fontSize:'0.85rem', fontWeight:600, color:'white', marginBottom:8}}>Live Statistics</div>
            <div className="lp-dash-stat">
              <span className="lp-dash-stat-val">24</span>
              <span className="lp-dash-stat-lbl">Threats Blocked</span>
              <span className="lp-dash-stat-sub">+12 today</span>
            </div>
            <div className="lp-dash-stat">
              <span className="lp-dash-stat-val">183</span>
              <span className="lp-dash-stat-lbl">Messages Filtered</span>
              <span className="lp-dash-stat-sub">+45 today</span>
            </div>
            <div className="lp-dash-stat">
              <span className="lp-dash-stat-val">7</span>
              <span className="lp-dash-stat-lbl">Suspicious Accounts</span>
              <span className="lp-dash-stat-sub">+2 today</span>
            </div>
            <div style={{marginTop:'auto'}}>
              <div className="lp-dash-stat" style={{marginBottom:16}}>
                <span className="lp-dash-stat-val" style={{fontSize:'1.2rem'}}>99.99%</span>
                <span className="lp-dash-stat-lbl">Uptime</span>
              </div>
              <div className="lp-dash-stat">
                <span className="lp-dash-stat-val" style={{fontSize:'1.2rem'}}>42ms</span>
                <span className="lp-dash-stat-lbl">Response Time</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const DemoChat = () => {
  const [step, setStep] = useState(0)
  useEffect(() => {
    const timer = setInterval(() => { setStep(s => (s + 1) % 5) }, 2000)
    return () => clearInterval(timer)
  }, [])

  return (
    <div style={{display:'flex', flexDirection:'column', gap:16, flex:1}}>
      <div className="lp-demo-chat">
        <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:8}}>
          <span style={{fontSize:'0.75rem', color:'#949ba4'}}>15:42</span>
          <span style={{fontSize:'0.75rem', color:'#949ba4'}}><AlertTriangle size={12} style={{display:'inline', verticalAlign:'middle'}}/> Suspicious User joined the server</span>
        </div>
        
        <AnimatePresence mode="popLayout">
          {step >= 1 && (
            <motion.div initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} className="lp-chat-msg">
              <div className="lp-chat-av" />
              <div>
                <div style={{display:'flex', alignItems:'baseline', gap:8}}>
                  <span className="lp-chat-name" style={{color:'#ef4444'}}>Suspicious User</span>
                  <span className="lp-chat-time">discord.gg/free-nitro</span>
                </div>
              </div>
            </motion.div>
          )}
          {step >= 2 && (
            <motion.div initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} className="lp-chat-msg">
              <div className="lp-chat-av" />
              <div>
                <div style={{display:'flex', alignItems:'baseline', gap:8}}>
                  <span className="lp-chat-name" style={{color:'#ef4444'}}>Suspicious User</span>
                  <span className="lp-chat-time">discord.gg/free-nitro</span>
                </div>
              </div>
            </motion.div>
          )}
          {step >= 3 && (
            <motion.div initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} className="lp-chat-msg">
              <div className="lp-chat-av" style={{background:'var(--cine-primary)', display:'flex', alignItems:'center', justifyContent:'center'}}><VortexLogo size={16} /></div>
              <div style={{width:'100%'}}>
                <div style={{display:'flex', alignItems:'baseline', gap:8}}>
                  <span className="lp-chat-name" style={{color:'var(--cine-primary)'}}>Vortex</span>
                  <span style={{background:'var(--cine-primary)', color:'white', fontSize:'0.6rem', padding:'2px 4px', borderRadius:4, fontWeight:700}}>APP</span>
                  <span className="lp-chat-time">15:42</span>
                </div>
                <div className="lp-chat-embed">
                  <div style={{display:'flex', alignItems:'center', gap:8, color:'white', fontWeight:700, marginBottom:8}}>
                    <CheckCircle2 size={16} color="var(--cine-success)"/> Threat neutralized
                  </div>
                  <div style={{fontSize:'0.8rem', color:'#dbdee1', marginBottom:4}}><span style={{fontWeight:700}}>Reason:</span> Repeated malicious links</div>
                  <div style={{fontSize:'0.8rem', color:'#dbdee1', marginBottom:4}}><span style={{fontWeight:700}}>Action:</span> Messages deleted and user quarantined</div>
                  <div style={{fontSize:'0.8rem', color:'#dbdee1'}}><span style={{fontWeight:700}}>Case ID:</span> #4821</div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      
      <div className="lp-demo-steps">
         <div className="lp-d-step"><div className="lp-d-num">1</div><div className="lp-d-text"><h5>User Joined</h5><p>Suspicious account detected</p></div></div>
         <div className="lp-d-step"><div className="lp-d-num">2</div><div className="lp-d-text"><h5>Spam Links Posted</h5><p>Malicious links detected</p></div></div>
         <div className="lp-d-step"><div className="lp-d-num">3</div><div className="lp-d-text"><h5>Messages Deleted</h5><p>28 messages removed</p></div></div>
         <div className="lp-d-step"><div className="lp-d-num">4</div><div className="lp-d-text"><h5>User Quarantined</h5><p>Account quarantined</p></div></div>
      </div>
      
      <div style={{display:'flex', justifyContent:'center', marginTop:16}}>
        <button className="lp-btn-primary" onClick={()=>setStep(0)} style={{padding:'8px 16px', fontSize:'0.8rem'}}><Zap size={14}/> Run Demo Again</button>
      </div>
    </div>
  )
}

function ScrollTextIcon(props) { return <ScrollText {...props}/> }

/* ── Main Page ─────────────────────────────────────────────────── */

export default function Landing() {
  return (
    <div className="lp-cinematic">
      <div className="lp-ambient">
        <div className="lp-ambient-light lp-light-1" />
        <div className="lp-ambient-light lp-light-2" />
        <div className="lp-ambient-light lp-light-3" />
      </div>

      <Nav />

      {/* Hero */}
      <section className="lp-hero">
        <div className="lp-hero-grid">
          <motion.div className="lp-hero-content" initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}>
            <div className="lp-tag"><VortexLogo size={14}/> #1 DISCORD MODERATION BOT</div>
            <h1>Moderation that <span>never</span> sleeps.</h1>
            <p>Protect your community with intelligent automoderation, advanced security, detailed logs, customizable commands, and powerful staff tools—all controlled from one command center.</p>
            <div className="lp-hero-buttons">
              <a href="/auth/invite" className="lp-btn-primary"><img src="https://assets-global.website-files.com/6257adef93867e50d84d30e2/636e0a6a49cf127bf92de1e2_icon_clyde_blurple_RGB.png" alt="Discord" style={{width:18, filter:'brightness(0) invert(1)'}}/> Add to Discord</a>
              <a href="#features" className="lp-btn-ghost">Explore Features</a>
            </div>
            <div className="lp-trust">
              <span><CheckCircle2 size={16}/> Fast setup</span>
              <span><Shield size={16}/> Powerful protection</span>
              <span><Users size={16}/> Built for every community</span>
            </div>
          </motion.div>
          
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 1, delay: 0.2 }}>
            <HeroMockup />
          </motion.div>
        </div>
      </section>

      {/* Live Strip */}
      <div className="lp-strip">
        <div className="lp-strip-inner">
          <div className="lp-strip-item"><CheckCircle2 size={18}/> Anti-Raid <span>Active</span></div>
          <div className="lp-strip-item"><CheckCircle2 size={18}/> AutoMod <span>Online</span></div>
          <div className="lp-strip-item"><CheckCircle2 size={18}/> Link Scanner <span>Active</span></div>
          <div className="lp-strip-item"><CheckCircle2 size={18}/> Backup Systems <span>Ready</span></div>
          <div className="lp-strip-item"><CheckCircle2 size={18}/> Audit Logs <span>Recording</span></div>
          <div className="lp-strip-item"><CheckCircle2 size={18}/> AI Detection <span>Monitoring</span></div>
          <div className="lp-strip-item" style={{marginLeft:'auto'}}><Activity size={18}/> System Status <span>All systems operational</span></div>
        </div>
      </div>

      {/* Features Bento */}
      <section className="lp-section" id="features">
        <div className="lp-section-header">
          <h2 className="lp-section-title">Everything your staff team needs. One powerful bot.</h2>
        </div>
        
        <div className="lp-bento">
          <div className="lp-bento-card">
            <div className="lp-bento-top">
              <div className="lp-bento-icon"><Zap size={18}/></div>
              <div>
                <div className="lp-bento-title">Intelligent AutoMod</div>
                <div className="lp-bento-desc">Detect spam, slurs, links, invites, mentions, and harmful content.</div>
              </div>
            </div>
            <div className="lp-bento-bottom">
              <div className="lp-mock-row"><span>AutoMod Rule</span> <span style={{color:'var(--cine-success)'}}>Enabled •</span></div>
              <div className="lp-mock-row"><span>Spam Detection</span> <div className="lp-mock-toggle" /></div>
              <div className="lp-mock-row" style={{marginTop:12}}><span>Punishment</span> <span>Timeout 10m ∨</span></div>
            </div>
          </div>
          
          <div className="lp-bento-card">
            <div className="lp-bento-top">
              <div className="lp-bento-icon" style={{background:'rgba(239,68,68,0.1)', color:'var(--cine-danger)'}}><Shield size={18}/></div>
              <div>
                <div className="lp-bento-title">Advanced Anti-Raid</div>
                <div className="lp-bento-desc">Stop raids before they harm your server with real-time detection.</div>
              </div>
            </div>
            <div className="lp-bento-bottom">
              <div className="lp-mock-row"><span>Raid Detection</span> <span style={{color:'var(--cine-danger)'}}>Elevated</span></div>
              <div className="lp-mock-graph" />
              <div className="lp-mock-row" style={{marginTop:4}}><span>Suspicious Joins</span> <span>15</span></div>
            </div>
          </div>
          
          <div className="lp-bento-card">
            <div className="lp-bento-top">
              <div className="lp-bento-icon" style={{background:'rgba(34,211,238,0.1)', color:'var(--cine-cyan)'}}><Terminal size={18}/></div>
              <div>
                <div className="lp-bento-title">Complete Toolkit</div>
                <div className="lp-bento-desc">All moderation tools in one place for fast and effective action.</div>
              </div>
            </div>
            <div className="lp-bento-bottom">
              <div className="lp-mock-cmd">/ban user</div>
              <div className="lp-mock-cmd">/kick user</div>
              <div className="lp-mock-cmd">/timeout user</div>
              <div className="lp-mock-cmd">/purge 100</div>
            </div>
          </div>
          
          <div className="lp-bento-card">
            <div className="lp-bento-top">
              <div className="lp-bento-icon" style={{background:'rgba(255,255,255,0.1)', color:'white'}}><Activity size={18}/></div>
              <div>
                <div className="lp-bento-title">Detailed Mod Logs</div>
                <div className="lp-bento-desc">Track everything with beautiful, searchable logs.</div>
              </div>
            </div>
            <div className="lp-bento-bottom">
              <div className="lp-mock-log"><time>15:42</time> <Shield size={12} color="var(--cine-danger)"/> User banned</div>
              <div className="lp-mock-log"><time>15:41</time> <MessageSquare size={12} color="var(--cine-cyan)"/> Message deleted</div>
              <div className="lp-mock-log"><time>15:40</time> <Settings size={12} color="var(--cine-warning)"/> Role updated</div>
            </div>
          </div>
          
          {/* Row 2 */}
          <div className="lp-bento-card">
            <div className="lp-bento-top">
              <div className="lp-bento-icon" style={{background:'rgba(16,185,129,0.1)', color:'var(--cine-success)'}}><Settings size={18}/></div>
              <div>
                <div className="lp-bento-title">Custom Rules</div>
                <div className="lp-bento-desc">Fully customize thresholds, punishments, and exemptions.</div>
              </div>
            </div>
            <div className="lp-bento-bottom">
              <div className="lp-mock-row"><span>Blocked Words</span> <span style={{color:'var(--cine-success)'}}>Enabled •</span></div>
              <div className="lp-mock-row"><span>Threshold</span> <span>5</span></div>
              <div className="lp-mock-row"><span>Punishment</span> <span>Timeout</span></div>
            </div>
          </div>
          
          <div className="lp-bento-card">
            <div className="lp-bento-top">
              <div className="lp-bento-icon" style={{background:'rgba(245,158,11,0.1)', color:'var(--cine-warning)'}}><Users size={18}/></div>
              <div>
                <div className="lp-bento-title">Staff Management</div>
                <div className="lp-bento-desc">Manage your team with roles, permissions, and activity stats.</div>
              </div>
            </div>
            <div className="lp-bento-bottom">
              <div style={{display:'flex', justifyContent:'space-between'}}>
                <div style={{display:'flex', flexDirection:'column'}}>
                  <span style={{fontSize:'0.7rem', color:'var(--cine-text-dim)'}}>Active Staff</span>
                  <span style={{fontSize:'1.5rem', fontWeight:700, color:'white'}}>24</span>
                </div>
                <div style={{display:'flex', flexDirection:'column', alignItems:'flex-end'}}>
                  <span style={{fontSize:'0.7rem', color:'var(--cine-text-dim)'}}>Cases Handled</span>
                  <span style={{fontSize:'1.5rem', fontWeight:700, color:'white'}}>1,248</span>
                </div>
              </div>
              <div className="lp-mock-graph" style={{borderTopColor:'var(--cine-success)', background:'linear-gradient(180deg, rgba(16,185,129,0.2) 0%, transparent 100%)', height: 20}} />
            </div>
          </div>
          
          <div className="lp-bento-card">
            <div className="lp-bento-top">
              <div className="lp-bento-icon" style={{background:'rgba(124,109,240,0.1)', color:'var(--cine-primary)'}}><Database size={18}/></div>
              <div>
                <div className="lp-bento-title">Server Backups</div>
                <div className="lp-bento-desc">Backup your server settings, roles, channels, and permissions.</div>
              </div>
            </div>
            <div className="lp-bento-bottom">
              <div className="lp-mock-row"><span>Last Backup</span> <span style={{color:'var(--cine-success)'}}>Status ∨</span></div>
              <div className="lp-mock-row"><span style={{color:'white', fontWeight:600}}>2m ago</span> <span style={{color:'var(--cine-success)'}}>Completed</span></div>
            </div>
          </div>
          
          <div className="lp-bento-card">
            <div className="lp-bento-top">
              <div className="lp-bento-icon" style={{background:'rgba(34,211,238,0.1)', color:'var(--cine-cyan)'}}><BarChart3 size={18}/></div>
              <div>
                <div className="lp-bento-title">Web Dashboard</div>
                <div className="lp-bento-desc">Manage everything from a powerful and modern dashboard.</div>
              </div>
            </div>
            <div className="lp-bento-bottom">
              <div className="lp-mock-row"><span>Dashboard</span> <span style={{color:'var(--cine-success)'}}>Online •</span></div>
              <div className="lp-mock-row"><span>Panels</span> <span style={{color:'white'}}>12</span></div>
            </div>
          </div>
        </div>
      </section>

      {/* Demo Split Section */}
      <section className="lp-section">
        <div className="lp-split">
          <div className="lp-split-panel">
            <h3 className="lp-split-title">Watch it stop trouble in real time.</h3>
            <DemoChat />
          </div>
          
          <div className="lp-split-panel">
            <h3 className="lp-split-title">Powerful commands. Simple control.</h3>
            <div className="lp-terminal-split">
              <div className="lp-term-left">
                <div className="lp-term-cmd">/ban user reason</div>
                <div className="lp-term-cmd">/warn user reason</div>
                <div className="lp-term-cmd">/timeout user duration</div>
                <div className="lp-term-cmd">/purge amount</div>
                <div className="lp-term-cmd">/lock channel</div>
                <div className="lp-term-cmd">/slowmode duration</div>
                <div className="lp-term-cmd">/case view</div>
                <div className="lp-term-cmd">/automod configure</div>
                <div className="lp-term-cmd">/raidmode enable</div>
                <div className="lp-term-cmd">/server backup</div>
              </div>
              <div className="lp-term-right">
                <div className="lp-term-res">User has been banned.</div>
                <div className="lp-term-res">User has been warned.</div>
                <div className="lp-term-res">User has been timed out.</div>
                <div className="lp-term-res">100 messages deleted.</div>
                <div className="lp-term-res">Channel has been locked.</div>
                <div className="lp-term-res">Slowmode set to 10s.</div>
                <div className="lp-term-res">Showing case #4821.</div>
                <div className="lp-term-res">AutoMod configured.</div>
                <div className="lp-term-res">Raid mode has been enabled.</div>
                <div className="lp-term-res">Server backup completed.</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Security Section */}
      <section className="lp-section" id="security">
        <div className="lp-security-split">
          <div className="lp-sec-content">
            <h2>Built to protect your server when everything goes wrong.</h2>
            <p>From spam and scams to coordinated raids and destructive staff actions, Vortex monitors your server continuously and responds before the damage spreads.</p>
            <div className="lp-sec-list">
              <div className="lp-sec-item"><Shield size={20}/> 99.99% Uptime</div>
              <div className="lp-sec-item"><Zap size={20}/> Millisecond Response Times</div>
              <div className="lp-sec-item"><Lock size={20}/> Permission-Safe Commands</div>
              <div className="lp-sec-item"><Database size={20}/> Encrypted Dashboard Sessions</div>
              <div className="lp-sec-item"><Search size={20}/> Full Audit History</div>
            </div>
            
            <div style={{marginTop: 60, position:'relative', width: 200, height: 200, display:'flex', alignItems:'center', justifyContent:'center'}}>
              <div style={{position:'absolute', inset:0, background:'radial-gradient(circle, rgba(124,109,240,0.3) 0%, transparent 70%)', borderRadius:'50%'}}/>
              <VortexLogo size={120} />
            </div>
          </div>
          
          <div className="lp-bottom-dash">
             <div className="lp-bd-main">
                <div style={{display:'flex', alignItems:'center', gap:12, marginBottom: 24, borderBottom:'1px solid var(--cine-border)', paddingBottom:16}}>
                  <div style={{width:24, height:24, background:'var(--cine-primary)', borderRadius:6, display:'flex', alignItems:'center', justifyContent:'center', color:'white'}}><VortexLogo size={12}/></div>
                  <span style={{fontWeight:600}}>Overview</span>
                </div>
                <div style={{display:'flex', gap:24, marginBottom:24}}>
                  <div>
                    <div style={{fontSize:'1.5rem', fontWeight:800}}>12,842</div>
                    <div style={{fontSize:'0.75rem', color:'var(--cine-text-muted)'}}>Members</div>
                  </div>
                  <div>
                    <div style={{fontSize:'1.5rem', fontWeight:800}}>156</div>
                    <div style={{fontSize:'0.75rem', color:'var(--cine-text-muted)'}}>Channels</div>
                  </div>
                  <div>
                    <div style={{fontSize:'1.5rem', fontWeight:800}}>24</div>
                    <div style={{fontSize:'0.75rem', color:'var(--cine-text-muted)'}}>Online</div>
                  </div>
                  <div>
                    <div style={{fontSize:'1.5rem', fontWeight:800}}>99.99%</div>
                    <div style={{fontSize:'0.75rem', color:'var(--cine-text-muted)'}}>Uptime</div>
                  </div>
                </div>
                <div style={{height: 150, background:'rgba(255,255,255,0.02)', border:'1px solid var(--cine-border)', borderRadius:8, display:'flex', alignItems:'flex-end', padding:16, gap:8}}>
                  <div style={{flex:1, height:'40%', background:'var(--cine-primary)', borderRadius:'4px 4px 0 0', opacity:0.8}}/>
                  <div style={{flex:1, height:'60%', background:'var(--cine-primary)', borderRadius:'4px 4px 0 0', opacity:0.8}}/>
                  <div style={{flex:1, height:'30%', background:'var(--cine-primary)', borderRadius:'4px 4px 0 0', opacity:0.8}}/>
                  <div style={{flex:1, height:'80%', background:'var(--cine-primary)', borderRadius:'4px 4px 0 0', opacity:0.8}}/>
                  <div style={{flex:1, height:'50%', background:'var(--cine-primary)', borderRadius:'4px 4px 0 0', opacity:0.8}}/>
                </div>
             </div>
             <div className="lp-bd-right">
                <div className="lp-bd-card">
                  <div className="lp-bd-icon" style={{background:'rgba(16,185,129,0.1)', color:'var(--cine-success)'}}><ShieldAlert size={16}/></div>
                  <div className="lp-bd-text"><h5>Raid Prevented</h5><p>15 suspicious joins blocked</p></div>
                </div>
                <div className="lp-bd-card">
                  <div className="lp-bd-icon" style={{background:'rgba(124,109,240,0.1)', color:'var(--cine-primary)'}}><Database size={16}/></div>
                  <div className="lp-bd-text"><h5>Backup Completed</h5><p>Server backup completed</p></div>
                </div>
                <div className="lp-bd-card">
                  <div className="lp-bd-icon" style={{background:'rgba(34,211,238,0.1)', color:'var(--cine-cyan)'}}><CheckCircle2 size={16}/></div>
                  <div className="lp-bd-text"><h5>Action Approved</h5><p>Moderator action approved</p></div>
                </div>
                <div className="lp-bd-card">
                  <div className="lp-bd-icon" style={{background:'rgba(239,68,68,0.1)', color:'var(--cine-danger)'}}><Lock size={16}/></div>
                  <div className="lp-bd-text"><h5>Link Blocked</h5><p>Malicious link blocked</p></div>
                </div>
             </div>
          </div>
        </div>
      </section>

      {/* Bottom Layout (3 Columns) */}
      <section className="lp-section" style={{paddingBottom: 0}}>
        <div className="lp-bottom-grid">
          <div className="lp-bg-col">
            <h3 className="lp-bg-title">Trusted by communities that take moderation seriously.</h3>
            <div className="lp-t-stats">
              <div className="lp-t-stat"><h4>25K+</h4><p>Servers Protected</p></div>
              <div className="lp-t-stat"><h4>3.2M+</h4><p>Users Monitored</p></div>
              <div className="lp-t-stat"><h4>1.7M+</h4><p>Threats Stopped</p></div>
              <div className="lp-t-stat"><h4>8.9M+</h4><p>Actions Completed</p></div>
            </div>
            
            <div className="lp-t-card">
              <div className="lp-t-av" style={{background:'#5865F2'}} />
              <div className="lp-t-info"><h5>Kevin</h5><p>Community Owner</p></div>
              <div style={{fontSize:'0.75rem', color:'var(--cine-text-dim)', marginLeft:'auto', maxWidth:120, textAlign:'right'}}>Vortex completely changed how we moderate.</div>
            </div>
            <div className="lp-t-card">
              <div className="lp-t-av" style={{background:'#f59e0b'}} />
              <div className="lp-t-info"><h5>Ava</h5><p>School Admin</p></div>
              <div style={{fontSize:'0.75rem', color:'var(--cine-text-dim)', marginLeft:'auto', maxWidth:120, textAlign:'right'}}>The automod is incredibly accurate, it catches everything.</div>
            </div>
          </div>
          
          <div className="lp-bg-col">
            <h3 className="lp-bg-title" style={{textAlign:'center'}}>Get started in 3 simple steps.</h3>
            <div className="lp-steps">
              <div className="lp-step">
                <div className="lp-step-num">1</div>
                <h5>Add the Bot</h5>
                <p>Invite Vortex to your Discord server.</p>
              </div>
              <div className="lp-step">
                <div className="lp-step-num">2</div>
                <h5>Choose Protection</h5>
                <p>Configure AutoMod, anti-raid, logs, staff roles, and more.</p>
              </div>
              <div className="lp-step">
                <div className="lp-step-num">3</div>
                <h5>Stay Protected</h5>
                <p>Vortex monitors your server 24/7 while you stay in control.</p>
              </div>
            </div>
            <a href="#" className="lp-btn-primary lp-step-btn"><Shield size={16}/> Protect My Server</a>
          </div>
          
          <div className="lp-bg-col">
            <div className="lp-cta-card">
               <h3 style={{fontSize:'1.5rem', fontWeight:800, marginBottom:16, lineHeight:1.2}}>Your community deserves better protection.</h3>
               <p>Set up Vortex in minutes and give your moderators the tools they need to keep your server safe, organized, and under control.</p>
               <div className="lp-cta-btns">
                 <a href="/auth/invite" className="lp-btn-primary"><img src="https://assets-global.website-files.com/6257adef93867e50d84d30e2/636e0a6a49cf127bf92de1e2_icon_clyde_blurple_RGB.png" alt="Discord" style={{width:16, filter:'brightness(0) invert(1)'}}/> Add to Discord</a>
                 <a href="/auth/login" className="lp-btn-ghost">Open Dashboard</a>
               </div>
               <div style={{fontSize:'0.75rem', color:'var(--cine-text-muted)'}}>Free to start. No complicated setup.</div>
               
               <div className="lp-cta-shield" style={{display:'flex', justifyContent:'center'}}>
                 <VortexLogo size={120} />
               </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="lp-footer">
        <div className="lp-footer-grid">
          <div className="lp-footer-col" style={{gridColumn:'span 2'}}>
            <div className="lp-logo" style={{marginBottom:16}}>
              <div className="lp-logo-icon"><VortexLogo size={20}/></div>
              VORTEX <span style={{fontWeight:400, fontSize:'0.7rem', letterSpacing:'1px', opacity:0.6, marginLeft:4}}>MODERATION</span>
            </div>
            <p style={{color:'var(--cine-text-muted)', fontSize:'0.8rem', lineHeight:1.6, maxWidth:250}}>The most advanced Discord moderation bot with intelligent automod and powerful staff tools.</p>
            
            <div style={{marginTop: 24}}>
              <div style={{fontSize:'0.75rem', fontWeight:700, color:'white', marginBottom:12}}>Community</div>
              <div style={{display:'flex', alignItems:'center', gap:8, fontSize:'0.8rem', color:'var(--cine-text-dim)'}}>
                <img src="https://assets-global.website-files.com/6257adef93867e50d84d30e2/636e0a6a49cf127bf92de1e2_icon_clyde_blurple_RGB.png" alt="Discord" style={{width:16, filter:'grayscale(1) opacity(0.7)'}}/> 12,842 Online
              </div>
            </div>
          </div>
          <div className="lp-footer-col">
            <h4>Product</h4>
            <a href="#features">Features</a>
            <Link to="/dashboard">Dashboard</Link>
            <a href="#security">Security</a>
            <a href="#">Updates</a>
          </div>
          <div className="lp-footer-col">
            <h4>Resources</h4>
            <a href="#commands">Commands</a>
            <a href="#">Documentation</a>
            <a href="#">Guides</a>
            <a href="#">API</a>
          </div>
          <div className="lp-footer-col">
            <h4>Support</h4>
            <a href="#">Support Center</a>
            <a href="#">Contact Us</a>
            <a href="#">Status</a>
            <a href="#">Report Bug</a>
          </div>
          <div className="lp-footer-col">
            <h4>Legal</h4>
            <a href="#">Terms of Service</a>
            <a href="#">Privacy Policy</a>
            <a href="#">Data Processing</a>
            <a href="#">DMCA</a>
          </div>
        </div>
        
        <div style={{maxWidth: 1500, margin: '40px auto 0', display:'flex', justifyContent:'flex-end'}}>
          <div style={{display:'flex', alignItems:'center', gap:40, background:'rgba(255,255,255,0.02)', border:'1px solid var(--cine-border)', padding:'12px 24px', borderRadius:8}}>
            <div>
              <div style={{fontSize:'0.8rem', fontWeight:700, color:'white', display:'flex', alignItems:'center', gap:8}}>System Status <CheckCircle2 size={12} color="var(--cine-success)"/></div>
              <div style={{fontSize:'0.7rem', color:'var(--cine-success)'}}>All systems operational</div>
            </div>
            <div className="lp-mock-graph" style={{width: 100, borderTopColor:'var(--cine-success)', background:'linear-gradient(180deg, rgba(16,185,129,0.2) 0%, transparent 100%)', marginTop:0, height:30}}/>
            <div style={{fontSize:'0.8rem', fontWeight:700, color:'var(--cine-success)'}}>99.99%</div>
          </div>
        </div>
      </footer>
    </div>
  )
}
