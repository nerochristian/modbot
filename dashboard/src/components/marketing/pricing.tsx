'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Check } from 'lucide-react'
import { SegmentedControl } from '@/components/ui/segmented'
import { buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type Plan = {
  name: string
  tagline: string
  monthly: number
  features: string[]
  highlighted?: boolean
  cta: string
}

const PLANS: Plan[] = [
  {
    name: 'Free',
    tagline: 'For a single server getting started.',
    monthly: 0,
    features: ['1 server', 'Core automod', 'Basic case tracking', 'Community support'],
    cta: 'Add to Discord',
  },
  {
    name: 'Pro',
    tagline: 'For growing communities that need more.',
    monthly: 9,
    highlighted: true,
    features: [
      'Unlimited automod rules',
      'Full case & infraction system',
      'Appeals workflow',
      'Custom widgets & saved views',
      'Roles & permissions',
      'Priority support',
    ],
    cta: 'Start free trial',
  },
  {
    name: 'Premium',
    tagline: 'For networks and communities at scale.',
    monthly: 29,
    features: [
      'Everything in Pro',
      'Multi-server management',
      'Raid shield & AI content scoring',
      'SAML SSO for your mod team',
      'Audit log exports',
      '99.99% uptime',
    ],
    cta: 'Contact us',
  },
]

export function Pricing() {
  const [cycle, setCycle] = useState<'monthly' | 'annual'>('monthly')

  return (
    <section id="pricing" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-24 sm:px-6">
      <div className="mx-auto max-w-2xl text-center">
        <span className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.18em] text-accent">Pricing</span>
        <h2 className="mt-3 font-display text-3xl font-semibold tracking-[-0.02em] text-foreground sm:text-4xl">
          One rate card. No surprises.
        </h2>
        <p className="mt-4 text-lg text-muted">
          Start with a 14-day free trial. No credit card required. Cancel anytime.
        </p>
        <div className="mt-6 flex items-center justify-center gap-3">
          <SegmentedControl
            aria-label="Billing cycle"
            value={cycle}
            onChange={setCycle}
            options={[
              { label: 'Monthly', value: 'monthly' },
              { label: 'Annual', value: 'annual' },
            ]}
          />
          <span className="rounded-sm bg-success-soft px-2.5 py-0.5 text-xs font-medium text-success">
            Save 20%
          </span>
        </div>
      </div>

      <div className="mt-14 grid gap-px overflow-hidden rounded-lg border border-border bg-border lg:grid-cols-3">
        {PLANS.map((plan) => {
          const price = cycle === 'annual' ? Math.round(plan.monthly * 0.8) : plan.monthly
          return (
            <div
              key={plan.name}
              className={cn(
                'relative flex flex-col p-7',
                plan.highlighted ? 'bg-surface-2' : 'bg-surface',
              )}
            >
              {plan.highlighted && (
                <span className="absolute right-0 top-0 rounded-bl-sm bg-accent px-2.5 py-0.5 font-mono text-[0.625rem] font-semibold uppercase tracking-[0.14em] text-accent-foreground">
                  Most popular
                </span>
              )}
              <h3 className="font-mono text-[0.6875rem] font-semibold uppercase tracking-[0.16em] text-accent">{plan.name}</h3>
              <p className="mt-2 text-sm text-muted">{plan.tagline}</p>
              <div className="mt-5 flex items-baseline gap-1">
                <span className="font-display text-4xl font-semibold tracking-tight text-foreground">${price}</span>
                <span className="text-sm text-muted">/mo</span>
              </div>
              {cycle === 'annual' && (
                <p className="mt-1 font-mono text-xs text-muted-2">billed annually (${price * 12}/yr)</p>
              )}
              <Link
                href="/register"
                className={cn(
                  buttonVariants({ variant: plan.highlighted ? 'primary' : 'outline', size: 'md' }),
                  'mt-6 w-full',
                )}
              >
                {plan.cta}
              </Link>
              <ul className="mt-6 space-y-3">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2.5 text-sm text-foreground">
                    <Check className="mt-0.5 size-4 shrink-0 text-success" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>
    </section>
  )
}
