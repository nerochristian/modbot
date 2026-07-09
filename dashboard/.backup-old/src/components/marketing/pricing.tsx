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
    name: 'Starter',
    tagline: 'For small teams getting started.',
    monthly: 29,
    features: ['Up to 3 seats', '10k tracked events', 'Core dashboards', 'CSV export', 'Email support'],
    cta: 'Start free trial',
  },
  {
    name: 'Pro',
    tagline: 'For growing teams that need more.',
    monthly: 99,
    highlighted: true,
    features: [
      'Up to 25 seats',
      '1M tracked events',
      'Advanced analytics & cohorts',
      'Custom widgets & saved views',
      'Roles & permissions',
      'Priority support',
    ],
    cta: 'Start free trial',
  },
  {
    name: 'Enterprise',
    tagline: 'For organizations at scale.',
    monthly: 499,
    features: [
      'Unlimited seats',
      'Unlimited events',
      'SAML SSO & audit logs',
      'Custom integrations',
      'Dedicated success manager',
      '99.99% uptime SLA',
    ],
    cta: 'Contact sales',
  },
]

export function Pricing() {
  const [cycle, setCycle] = useState<'monthly' | 'annual'>('monthly')

  return (
    <section id="pricing" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-24 sm:px-6">
      <div className="mx-auto max-w-2xl text-center">
        <span className="text-sm font-semibold text-accent">Pricing</span>
        <h2 className="mt-2 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
          Simple, transparent pricing
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
          <span className="rounded-full bg-success-soft px-2.5 py-0.5 text-xs font-medium text-success">
            Save 20%
          </span>
        </div>
      </div>

      <div className="mt-14 grid gap-6 lg:grid-cols-3">
        {PLANS.map((plan) => {
          const price = cycle === 'annual' ? Math.round(plan.monthly * 0.8) : plan.monthly
          return (
            <div
              key={plan.name}
              className={cn(
                'relative flex flex-col rounded-2xl border p-6',
                plan.highlighted
                  ? 'border-accent bg-card shadow-xl shadow-accent/10 ring-1 ring-accent'
                  : 'border-border bg-card',
              )}
            >
              {plan.highlighted && (
                <span className="absolute -top-3 left-6 rounded-full bg-accent px-3 py-1 text-xs font-semibold text-accent-foreground">
                  Most popular
                </span>
              )}
              <h3 className="text-lg font-semibold text-foreground">{plan.name}</h3>
              <p className="mt-1 text-sm text-muted">{plan.tagline}</p>
              <div className="mt-5 flex items-baseline gap-1">
                <span className="text-4xl font-bold tracking-tight text-foreground">${price}</span>
                <span className="text-sm text-muted">/mo</span>
              </div>
              {cycle === 'annual' && (
                <p className="mt-1 text-xs text-muted-2">billed annually (${price * 12}/yr)</p>
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
