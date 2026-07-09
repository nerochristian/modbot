'use client'

import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

const FAQS = [
  {
    q: 'How long does it take to get set up?',
    a: 'Most teams are up and running in under 10 minutes. Sign up, connect a data source (or use our sample data), and your dashboards populate automatically. No engineering required for the core setup.',
  },
  {
    q: 'Can I customize the dashboards?',
    a: 'Extensively. Every user can reorder, show, or hide widgets, switch chart types, choose date ranges, pick a theme and accent color, adjust layout density, and save custom views — all persisted to their account.',
  },
  {
    q: 'Do you support roles and permissions?',
    a: 'Yes. Nebula ships with Admin, Manager, and Viewer roles out of the box, and admins can edit the exact permission matrix per role at any time. UI visibility and API access are both enforced against permissions.',
  },
  {
    q: 'Is my data secure?',
    a: 'Sessions use signed, httpOnly cookies with server-side revocation, passwords are hashed with bcrypt, and every sensitive action is written to an immutable audit log. Enterprise plans add SAML SSO and 2FA enforcement.',
  },
  {
    q: 'Can I export my data?',
    a: 'Anytime. Export any table or report as CSV, JSON, XLSX, or PDF. Server-side filtering and sorting mean exports reflect exactly what you see on screen.',
  },
  {
    q: 'What happens after the free trial?',
    a: 'Your data stays intact. Choose a plan to keep going, or downgrade to a limited free tier. We will never delete your data without warning, and there are no cancellation fees.',
  },
]

export function Faq() {
  const [open, setOpen] = useState<number | null>(0)

  return (
    <section id="faq" className="mx-auto max-w-3xl scroll-mt-20 px-4 py-24 sm:px-6">
      <div className="text-center">
        <span className="text-sm font-semibold text-accent">FAQ</span>
        <h2 className="mt-2 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
          Frequently asked questions
        </h2>
        <p className="mt-4 text-lg text-muted">Everything you need to know about the product.</p>
      </div>

      <div className="mt-12 divide-y divide-border rounded-2xl border border-border bg-card">
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
