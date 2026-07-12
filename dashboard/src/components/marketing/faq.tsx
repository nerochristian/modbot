'use client'

import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

const FAQS = [
  {
    q: 'How long does it take to get set up?',
    a: 'Most servers are protected in under 10 minutes. Add the bot to your server, invite your mod team, and turn on a starter automod ruleset — your command deck populates automatically. No engineering required for the core setup.',
  },
  {
    q: 'Can I customize how moderation works?',
    a: 'Extensively. Build layered automod rules with your own severity thresholds and actions, then let every moderator reorder, show, or hide deck widgets, choose date ranges, pick a theme and accent color, adjust density, and save custom views — all persisted to their account.',
  },
  {
    q: 'Do you support roles and permissions?',
    a: 'Yes. Docket ships with Admin, Moderator, and Helper roles out of the box, and admins can edit the exact permission matrix per role at any time. Console visibility and API access are both enforced against permissions.',
  },
  {
    q: 'Is my data secure?',
    a: 'Sessions use signed, httpOnly cookies with server-side revocation, passwords are hashed with bcrypt, and every moderation action is written to an immutable audit log. Premium plans add SAML SSO and 2FA enforcement for your mod team.',
  },
  {
    q: 'Can I export cases and member data?',
    a: 'Anytime. Export any case, member list, or report as CSV, JSON, XLSX, or PDF. Server-side filtering and sorting mean exports reflect exactly what you see on screen.',
  },
  {
    q: 'What happens after the free trial?',
    a: 'Your cases, rules, and audit history stay intact. Choose a plan to keep going, or downgrade to the limited free tier. We will never delete your data without warning, and there are no cancellation fees.',
  },
]

export function Faq() {
  const [open, setOpen] = useState<number | null>(0)

  return (
    <section id="faq" className="mx-auto max-w-3xl scroll-mt-20 px-4 py-24 sm:px-6">
      <div className="text-center">
        <span className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">FAQ</span>
        <h2 className="mt-3 font-display text-3xl font-semibold tracking-[-0.02em] text-foreground sm:text-4xl">
          Questions, on the record
        </h2>
        <p className="mt-4 text-lg text-muted">Everything you need to know before you file the first case.</p>
      </div>

      <div className="mt-12 divide-y divide-border rounded-lg border border-border bg-card">
        {FAQS.map((item, i) => {
          const isOpen = open === i
          return (
            <div key={item.q}>
              <button
                onClick={() => setOpen(isOpen ? null : i)}
                className="focus-ring flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
                aria-expanded={isOpen}
              >
                <span className="text-sm font-medium text-foreground sm:text-base">{item.q}</span>
                <ChevronDown
                  className={cn(
                    'size-5 shrink-0 text-muted transition-transform',
                    isOpen && 'rotate-180',
                  )}
                />
              </button>
              <div
                className={cn(
                  'grid transition-all duration-200',
                  isOpen ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0',
                )}
              >
                <div className="overflow-hidden">
                  <p className="px-5 pb-5 text-sm leading-relaxed text-muted">{item.a}</p>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
