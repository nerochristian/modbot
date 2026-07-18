import type { Metadata } from 'next'
import Link from 'next/link'
import {
  ArrowRight,
  Check,
  CircleDot,
  Command,
  FileClock,
  Gavel,
  MessageSquareWarning,
  ShieldCheck,
} from 'lucide-react'
import styles from './marketing.module.css'

export const metadata: Metadata = {
  title: 'Docket — Discord moderation, kept in order',
  description:
    'Detect raids, enforce clear rules, keep complete case records, and handle appeals from one Discord moderation workspace.',
}

const capabilities = [
  'Raid patterns',
  'Spam bursts',
  'Harmful links',
  'Repeat evasion',
  'Verification abuse',
]

const commandChecks = [
  'Target and duration confirmed',
  'Reason attached to the case',
  'Action written to the audit trail',
]

export default function LandingPage() {
  return (
    <>
      <section className={styles.hero} aria-labelledby="hero-title">
        <div className={styles.heroGrid}>
          <div className={styles.heroCopy}>
            <div className={styles.eyebrow}>
              <CircleDot aria-hidden="true" size={13} />
              Moderation operations / online
            </div>
            <h1 id="hero-title">
              Your server stays loud.
              <span>The pile-on doesn&apos;t.</span>
            </h1>
            <p className={styles.heroLead}>
              Docket catches fast-moving abuse, gives moderators a clear decision queue,
              and keeps the full record when someone asks what happened.
            </p>
            <div className={styles.heroActions}>
              <Link className={styles.primaryAction} href="/api/auth/discord/authorize">
                Open your command desk
                <ArrowRight aria-hidden="true" size={17} />
              </Link>
              <a className={styles.textAction} href="#workflow">
                See the response flow
              </a>
            </div>
            <div className={styles.trustLine}>
              <ShieldCheck aria-hidden="true" size={16} />
              Uses your Discord permissions. Nothing new to memorize.
            </div>
          </div>

          <div className={styles.incidentStage} aria-label="Preview of a moderated raid incident">
            <div className={styles.caseClock} aria-hidden="true">
              <span>00</span><i>:</i><span>02</span><i>:</i><span>14</span>
            </div>
            <div className={styles.incidentPanel}>
              <div className={styles.panelTopline}>
                <span>INCIDENT / 1842</span>
                <span className={styles.liveStatus}><i /> CONTAINED</span>
              </div>
              <div className={styles.channelLine}>
                <span># general</span>
                <span>4:17:02 AM</span>
              </div>
              <div className={`${styles.eventRow} ${styles.eventOne}`}>
                <div className={styles.eventAvatar}>MX</div>
                <div>
                  <div className={styles.eventMeta}><strong>mixer_07</strong><span>new account</span></div>
                  <p>same link posted 8× across 3 channels</p>
                </div>
              </div>
              <div className={`${styles.eventRow} ${styles.eventTwo}`}>
                <div className={`${styles.eventAvatar} ${styles.botAvatar}`}><ShieldCheck size={15} /></div>
                <div>
                  <div className={styles.eventMeta}><strong>Docket</strong><span>automod</span></div>
                  <p>Messages removed. Account timed out for 30 minutes.</p>
                </div>
              </div>
              <div className={`${styles.eventRow} ${styles.eventThree}`}>
                <div className={`${styles.eventAvatar} ${styles.modAvatar}`}>AP</div>
                <div>
                  <div className={styles.eventMeta}><strong>Alex / moderator</strong><span>reviewed</span></div>
                  <p>Linked two related accounts and closed the incident.</p>
                </div>
              </div>
              <div className={styles.panelFooter}>
                <span><FileClock aria-hidden="true" size={14} /> Case record saved</span>
                <span>02:14 to containment</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.capabilityRail} aria-label="Threats Docket can detect">
        <div className={styles.railInner}>
          <span className={styles.railLabel}>WATCHING FOR</span>
          {capabilities.map((capability) => (
            <span key={capability}><i />{capability}</span>
          ))}
        </div>
      </section>

      <section className={styles.workflow} id="workflow" aria-labelledby="workflow-title">
        <div className={styles.sectionIntro}>
          <span className={styles.sectionLabel}>THE RESPONSE FLOW</span>
          <h2 id="workflow-title">One calm queue after a loud night.</h2>
          <p>
            Signals arrive messy. Docket turns them into work your team can review,
            assign, and finish without digging through channel history.
          </p>
        </div>

        <div className={styles.queueFrame}>
          <div className={styles.queueHeader}>
            <div>
              <span>ACTIVE CASELOAD</span>
              <strong>7 items need a decision</strong>
            </div>
            <div className={styles.queueTabs} aria-hidden="true">
              <span className={styles.activeTab}>Open 7</span><span>Assigned 3</span><span>Closed</span>
            </div>
          </div>
          <div className={styles.queueColumns} aria-hidden="true">
            <span>Signal</span><span>Member</span><span>Context</span><span>Owner</span><span>State</span>
          </div>
          <div className={styles.queueRow}>
            <span className={styles.severityHigh}>RAID CLUSTER</span>
            <strong>mixer_07 + 2</strong>
            <span>8 duplicate links / 3 channels</span>
            <span>Alex P.</span>
            <span className={styles.stateContained}>Contained</span>
          </div>
          <div className={styles.queueRow}>
            <span className={styles.severityMedium}>EVASION</span>
            <strong>nightshift</strong>
            <span>Matched prior ban fingerprint</span>
            <span>Unassigned</span>
            <span className={styles.stateReview}>Review</span>
          </div>
          <div className={styles.queueRow}>
            <span className={styles.severityLow}>REPORT</span>
            <strong>solace</strong>
            <span>Member report with 4 messages</span>
            <span>Mina K.</span>
            <span className={styles.stateOpen}>Open</span>
          </div>
          <div className={styles.queueFooter}>
            <span>Every row opens the messages, member history, action, and notes together.</span>
            <ArrowRight aria-hidden="true" size={18} />
          </div>
        </div>
      </section>

      <section className={styles.controls} id="controls" aria-labelledby="controls-title">
        <div className={styles.controlsGrid}>
          <div className={styles.controlsCopy}>
            <span className={styles.sectionLabel}>CONTROLS PEOPLE CAN READ</span>
            <h2 id="controls-title">Rules that sound like rules.</h2>
            <p>
              Build enforcement in plain language, preview the effect, and keep exceptions
              beside the rule instead of buried in a config file.
            </p>
            <ul>
              <li><Check aria-hidden="true" size={16} /> Know what triggers before enabling it</li>
              <li><Check aria-hidden="true" size={16} /> Escalate repeat behavior without overreacting</li>
              <li><Check aria-hidden="true" size={16} /> Explain every automated action to moderators</li>
            </ul>
          </div>
          <div className={styles.ruleBuilder} aria-label="Example moderation rule">
            <div className={styles.ruleHeader}>
              <div><MessageSquareWarning aria-hidden="true" size={18} /><span>Link burst</span></div>
              <span className={styles.ruleOn}>ENABLED</span>
            </div>
            <div className={styles.ruleSentence}>
              <span>When</span>
              <strong>a new member</strong>
              <span>posts</span>
              <strong>6 or more links</strong>
              <span>within</span>
              <strong>12 seconds</strong>
            </div>
            <div className={styles.ruleOutcome}>
              <span>THEN</span>
              <div><Check size={14} /> Remove matching messages</div>
              <div><Check size={14} /> Timeout member for 30 minutes</div>
              <div><Check size={14} /> Open a case with message evidence</div>
            </div>
            <div className={styles.ruleNote}>Trusted roles and approved domains are excluded.</div>
          </div>
        </div>
      </section>

      <section className={styles.recordSection} aria-labelledby="record-title">
        <div className={styles.sectionIntro}>
          <span className={styles.sectionLabel}>THE RECORD SURVIVES THE MOMENT</span>
          <h2 id="record-title">Every decision keeps its context.</h2>
          <p>
            The message, moderator action, reason, and appeal stay attached to the same case.
            No screenshot archaeology. No conflicting spreadsheets.
          </p>
        </div>
        <div className={styles.recordGrid}>
          <article className={styles.recordCard}>
            <div className={styles.recordIcon}><Gavel aria-hidden="true" size={20} /></div>
            <span className={styles.recordKicker}>CASE / D-1842</span>
            <h3>Decision history</h3>
            <div className={styles.historyLine}><i /><span><strong>04:17</strong> Link burst detected</span></div>
            <div className={styles.historyLine}><i /><span><strong>04:17</strong> 30 minute timeout applied</span></div>
            <div className={styles.historyLine}><i /><span><strong>04:19</strong> Incident closed by Alex</span></div>
          </article>
          <article className={`${styles.recordCard} ${styles.appealCard}`}>
            <div className={styles.recordIcon}><FileClock aria-hidden="true" size={20} /></div>
            <span className={styles.recordKicker}>APPEAL / RECEIVED 11:32</span>
            <h3>Review with the facts beside it.</h3>
            <blockquote>“I joined from a shared invite and didn&apos;t realize the link was posting twice.”</blockquote>
            <div className={styles.appealMeta}>
              <span>Original messages</span><strong>8 attached</strong>
              <span>Prior cases</span><strong>None</strong>
              <span>Reviewer</span><strong>Mina K.</strong>
            </div>
          </article>
        </div>
      </section>

      <section className={styles.commandSection} aria-labelledby="command-title">
        <div className={styles.commandCopy}>
          <Command aria-hidden="true" size={22} />
          <span className={styles.sectionLabel}>FROM DISCORD OR THE DASHBOARD</span>
          <h2 id="command-title">Act where the incident happens.</h2>
          <p>Use familiar commands in Discord. Docket confirms the target, duration, and reason before the action becomes part of the permanent record.</p>
          <Link href="/commands">Explore every command <ArrowRight aria-hidden="true" size={16} /></Link>
        </div>
        <div className={styles.commandTerminal}>
          <div className={styles.terminalTop}><span># mod-ops</span><span>Docket is online</span></div>
          <div className={styles.terminalLine}><span>Alex</span><code>/timeout @mixer_07 30m repeated link spam</code></div>
          <div className={styles.commandResult}>
            <div className={styles.resultHead}><ShieldCheck size={17} /><strong>Ready to apply timeout</strong></div>
            <dl>
              <div><dt>Member</dt><dd>@mixer_07</dd></div>
              <div><dt>Duration</dt><dd>30 minutes</dd></div>
              <div><dt>Reason</dt><dd>Repeated link spam</dd></div>
            </dl>
            <div className={styles.confirmButton}>Confirm timeout</div>
          </div>
          <ul className={styles.commandChecks}>
            {commandChecks.map((item) => <li key={item}><Check size={13} />{item}</li>)}
          </ul>
        </div>
      </section>

      <section className={styles.finalCta}>
        <div>
          <span className={styles.sectionLabel}>YOUR NEXT INCIDENT WILL HAVE A RECORD</span>
          <h2>Give your mod team one place to act.</h2>
        </div>
        <Link className={styles.finalAction} href="/api/auth/discord/authorize">
          Start with Discord
          <ArrowRight aria-hidden="true" size={19} />
        </Link>
      </section>
    </>
  )
}
