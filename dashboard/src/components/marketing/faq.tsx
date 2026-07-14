'use client'

import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

const FAQS = [
  {
    q: 'Who can open the dashboard?',
    a: 'Only the server owner or someone whose live Discord permissions include Administrator can select that server and enter its dashboard.',
  },
  {
    q: 'Does the dashboard use real Discord data?',
    a: 'Yes. Signed-in workspaces load the selected server’s Discord members, roles, channels, and recorded moderation activity. Any examples on the public landing page are clearly labeled as preview data.',
  },
  {
    q: 'What can automod handle?',
    a: 'You can configure rules for blocked words, spam, links, invites, duplicate messages, mention floods, caps, and raid behavior, including the action taken when a rule triggers.',
  },
  {
    q: 'How do member reports work?',
    a: 'A normal member or staff member can use /report. The report is stored for the server’s moderation team to review and update without posting the details publicly.',
  },
  {
    q: 'Can I configure ticket questions?',
    a: 'Yes. Ticket settings let you choose the panel options, the questions asked for each option, an optional emoji, staff access, routing, and transcript logging.',
  },
  {
    q: 'Where can I see every command?',
    a: 'Open the Commands page from this website, or use /help or ,help in Discord to get the same help destination.',
  },
]

export function Faq() {
  const [open, setOpen] = useState<number | null>(0)

  return (
    <section id="faq" className="mx-auto max-w-3xl scroll-mt-20 px-4 py-24 sm:px-6">
      <div className="text-center">
        <span className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">FAQ</span>
        <h2 className="mt-3 font-display text-3xl font-semibold tracking-[-0.02em] text-foreground sm:text-4xl">
          Common questions
        </h2>
        <p className="mt-4 text-lg text-muted">Straight answers about access, setup, and everyday moderation.</p>
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
