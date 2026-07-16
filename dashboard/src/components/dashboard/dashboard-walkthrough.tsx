'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, ArrowRight, Blocks, Check, Gavel, Radar, ShieldCheck, X } from 'lucide-react'
import { Button, buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const STEPS = [
  {
    eyebrow: 'Orientation / 01',
    title: 'This is your moderation desk',
    description: 'Docket turns your server activity into one operating view. You can configure protection, review cases, and follow every staff action from here.',
    icon: Radar,
    action: null,
  },
  {
    eyebrow: 'Systems / 02',
    title: 'Choose what Docket runs',
    description: 'Modules is where you enable verification, AutoMod, tickets, welcome cards, logging, and the rest of Docket. Every switch applies to this server only.',
    icon: Blocks,
    action: { label: 'Open modules', href: '/dashboard/modules' },
  },
  {
    eyebrow: 'Protection / 03',
    title: 'Tune AutoMod before traffic arrives',
    description: 'Start with the recommended rule set, then adjust thresholds and enforcement. Hits appear in activity and can create cases automatically.',
    icon: ShieldCheck,
    action: { label: 'Configure AutoMod', href: '/dashboard/automod' },
  },
  {
    eyebrow: 'Records / 04',
    title: 'Every decision leaves a record',
    description: 'Cases, appeals, court activity, and audit history are kept together, so staff can reconstruct what happened without searching Discord.',
    icon: Gavel,
    action: { label: 'Review cases', href: '/dashboard/cases' },
  },
] as const

export function DashboardWalkthrough({
  guildId,
  guildName,
  restartToken,
}: {
  guildId: string
  guildName: string
  restartToken: number
}) {
  const storageKey = useMemo(() => `docket:walkthrough:v1:${guildId}`, [guildId])
  const [open, setOpen] = useState(false)
  const [step, setStep] = useState(0)

  useEffect(() => {
    if (restartToken > 0 || window.localStorage.getItem(storageKey) !== 'complete') {
      const timer = window.setTimeout(() => {
        setStep(0)
        setOpen(true)
      }, 0)
      return () => window.clearTimeout(timer)
    }
  }, [restartToken, storageKey])

  const finish = useCallback(() => {
    window.localStorage.setItem(storageKey, 'complete')
    setOpen(false)
  }, [storageKey])

  useEffect(() => {
    if (!open) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') finish()
      if (event.key === 'ArrowRight' && step < STEPS.length - 1) setStep((value) => value + 1)
      if (event.key === 'ArrowLeft' && step > 0) setStep((value) => value - 1)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => {
      document.body.style.overflow = previous
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [finish, open, step])

  if (!open) return null
  const current = STEPS[step]
  const CurrentIcon = current.icon
  const last = step === STEPS.length - 1

  return (
    <div className="fixed inset-0 z-[100] grid place-items-center overflow-y-auto bg-ink/70 p-4 backdrop-blur-sm" role="presentation">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="walkthrough-title"
        className="relative grid w-full max-w-4xl overflow-hidden rounded-2xl border border-accent-line bg-card shadow-[0_40px_120px_-36px_rgba(0,0,0,.85)] md:grid-cols-[15rem_minmax(0,1fr)]"
      >
        <button
          type="button"
          onClick={finish}
          className="focus-ring absolute right-4 top-4 z-10 rounded-lg p-2 text-muted-2 hover:bg-surface-2 hover:text-foreground"
          aria-label="Close walkthrough"
        >
          <X className="size-4" />
        </button>

        <aside className="border-b border-border bg-surface-2/80 p-6 md:border-b-0 md:border-r">
          <p className="font-mono text-[0.625rem] font-bold uppercase tracking-[0.18em] text-accent">First deployment</p>
          <p className="mt-2 font-display text-lg font-semibold text-foreground">{guildName}</p>
          <p className="mt-1 text-xs leading-5 text-muted">Four checkpoints to put your server under Docket.</p>
          <ol className="mt-6 grid grid-cols-4 gap-2 md:grid-cols-1 md:gap-0">
            {STEPS.map((item, index) => {
              const complete = index < step
              const active = index === step
              return (
                <li key={item.eyebrow} className="relative md:pb-7 last:pb-0">
                  {index < STEPS.length - 1 && <span className="absolute left-[0.68rem] top-6 hidden h-full w-px bg-border md:block" />}
                  <button
                    type="button"
                    onClick={() => setStep(index)}
                    className="group relative flex w-full flex-col items-center gap-2 text-left md:flex-row md:items-center md:gap-3"
                    aria-current={active ? 'step' : undefined}
                  >
                    <span className={cn(
                      'relative z-[1] grid size-6 shrink-0 place-items-center rounded-full border font-mono text-[0.625rem] font-bold transition-colors',
                      complete ? 'border-success bg-success text-white' : active ? 'border-accent bg-accent text-white' : 'border-border-strong bg-card text-muted-2',
                    )}>
                      {complete ? <Check className="size-3.5" /> : index + 1}
                    </span>
                    <span className={cn('hidden text-xs font-medium md:block', active ? 'text-foreground' : 'text-muted group-hover:text-foreground')}>
                      {item.title}
                    </span>
                  </button>
                </li>
              )
            })}
          </ol>
        </aside>

        <div className="flex min-h-[28rem] flex-col p-7 sm:p-10">
          <div className="grid size-12 place-items-center rounded-xl border border-accent-line bg-accent-soft text-accent">
            <CurrentIcon className="size-5" />
          </div>
          <p className="mt-8 font-mono text-[0.625rem] font-bold uppercase tracking-[0.18em] text-accent">{current.eyebrow}</p>
          <h2 id="walkthrough-title" className="mt-2 max-w-xl font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            {current.title}
          </h2>
          <p className="mt-4 max-w-xl text-sm leading-7 text-muted sm:text-base">{current.description}</p>

          {current.action && (
            <Link href={current.action.href} onClick={finish} className={cn(buttonVariants({ variant: 'secondary', size: 'sm' }), 'mt-6 w-fit')}>
              {current.action.label} <ArrowRight className="size-3.5" />
            </Link>
          )}

          <div className="mt-auto flex flex-col-reverse gap-3 border-t border-border pt-6 sm:flex-row sm:items-center sm:justify-between">
            <button type="button" onClick={finish} className="text-xs font-medium text-muted hover:text-foreground">Skip walkthrough</button>
            <div className="flex items-center justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setStep((value) => value - 1)} disabled={step === 0}>
                <ArrowLeft className="size-3.5" /> Back
              </Button>
              {last ? (
                <Button size="sm" onClick={finish}>Finish setup <Check className="size-3.5" /></Button>
              ) : (
                <Button size="sm" onClick={() => setStep((value) => value + 1)}>Next <ArrowRight className="size-3.5" /></Button>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
