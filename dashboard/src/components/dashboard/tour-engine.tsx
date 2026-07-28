'use client'

import { useCallback, useEffect, useLayoutEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import Link from 'next/link'
import { ArrowLeft, ArrowRight, Check, X } from 'lucide-react'
import { Button, buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export type TourStep = {
  /** `data-tour` attribute value of the element to spotlight. Omit for a centered step. */
  target?: string
  eyebrow?: string
  title: string
  description: string
  action?: { label: string; href: string }
}

const TOOLTIP_WIDTH = 320
const TOOLTIP_HEIGHT = 210
const PAD = 8

/**
 * Spotlight guided tour: highlights real UI behind `data-tour` anchors with a
 * cutout overlay and a positioned tooltip. Completion is remembered per
 * storageKey; pass a bumping `restartToken` to re-run on demand.
 */
export function GuidedTour({
  steps,
  storageKey,
  restartToken = 0,
  onFinish,
}: {
  steps: readonly TourStep[]
  storageKey: string
  restartToken?: number
  onFinish?: () => void
}) {
  const [open, setOpen] = useState(false)
  const [index, setIndex] = useState(0)
  const [rect, setRect] = useState<DOMRect | null>(null)

  useEffect(() => {
    if (restartToken > 0 || window.localStorage.getItem(storageKey) !== 'complete') {
      const timer = window.setTimeout(() => {
        setIndex(0)
        setOpen(true)
      }, 700)
      return () => window.clearTimeout(timer)
    }
  }, [restartToken, storageKey])

  const step = steps[index]
  const last = index === steps.length - 1

  const locate = useCallback(() => {
    if (!step?.target) {
      setRect(null)
      return
    }
    const element = document.querySelector(`[data-tour="${step.target}"]`)
    if (!element) {
      setRect(null)
      return
    }
    element.scrollIntoView({ block: 'nearest' })
    setRect(element.getBoundingClientRect())
  }, [step])

  useLayoutEffect(() => {
    if (!open) return
    locate()
    window.addEventListener('resize', locate)
    window.addEventListener('scroll', locate, true)
    return () => {
      window.removeEventListener('resize', locate)
      window.removeEventListener('scroll', locate, true)
    }
  }, [locate, open])

  const finish = useCallback(() => {
    window.localStorage.setItem(storageKey, 'complete')
    setOpen(false)
    onFinish?.()
  }, [onFinish, storageKey])

  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') finish()
      if (event.key === 'ArrowRight') {
        if (last) finish()
        else setIndex((value) => Math.min(steps.length - 1, value + 1))
      }
      if (event.key === 'ArrowLeft') setIndex((value) => Math.max(0, value - 1))
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [finish, last, open, steps.length])

  if (!open || typeof document === 'undefined') return null

  const tooltipStyle: React.CSSProperties = rect
    ? (() => {
        const centerX = Math.min(
          Math.max(rect.left + rect.width / 2, 16 + TOOLTIP_WIDTH / 2),
          window.innerWidth - 16 - TOOLTIP_WIDTH / 2,
        )
        const below = rect.bottom + 14
        const fitsBelow = below + TOOLTIP_HEIGHT < window.innerHeight
        const top = fitsBelow ? below : Math.max(16, rect.top - 14 - TOOLTIP_HEIGHT)
        return { left: centerX, top, transform: 'translateX(-50%)' }
      })()
    : { left: '50%', top: '50%', transform: 'translate(-50%, -50%)' }

  return createPortal(
    <div className="fixed inset-0 z-[100]" role="presentation">
      {rect ? (
        <div
          className="pointer-events-none absolute rounded-xl border-2 border-accent transition-all duration-300 ease-out"
          style={{
            left: rect.left - PAD,
            top: rect.top - PAD,
            width: rect.width + PAD * 2,
            height: rect.height + PAD * 2,
            boxShadow: '0 0 0 9999px color-mix(in srgb, var(--ink) 62%, transparent)',
          }}
        />
      ) : (
        <div className="absolute inset-0 bg-ink/60 backdrop-blur-[2px]" />
      )}

      <section
        role="dialog"
        aria-modal="true"
        aria-label={`${step.title} (step ${index + 1} of ${steps.length})`}
        className="animate-fade-in absolute w-80 rounded-2xl border border-border bg-surface p-5 shadow-[0_30px_90px_-30px_rgba(0,0,0,.7)]"
        style={tooltipStyle}
      >
        <button
          type="button"
          onClick={finish}
          aria-label="Close tour"
          className="focus-ring absolute right-3 top-3 rounded-md p-1 text-muted-2 hover:bg-surface-2 hover:text-foreground"
        >
          <X className="size-4" />
        </button>

        {step.eyebrow && (
          <p className="font-mono text-[0.625rem] font-bold uppercase tracking-[0.18em] text-accent">{step.eyebrow}</p>
        )}
        <h2 className="mt-1.5 font-display text-lg font-semibold tracking-tight text-foreground">{step.title}</h2>
        <p className="mt-2 text-sm leading-6 text-muted">{step.description}</p>

        {step.action && (
          <Link href={step.action.href} onClick={finish} className={cn(buttonVariants({ variant: 'secondary', size: 'sm' }), 'mt-4 w-fit')}>
            {step.action.label} <ArrowRight className="size-3.5" />
          </Link>
        )}

        <div className="mt-5 flex items-center justify-between border-t border-border pt-4">
          <div className="flex items-center gap-1.5">
            {steps.map((_, dot) => (
              <span
                key={dot}
                className={cn(
                  'size-1.5 rounded-full transition-colors',
                  dot === index ? 'bg-accent' : dot < index ? 'bg-success' : 'bg-border-strong',
                )}
              />
            ))}
          </div>
          <div className="flex items-center gap-2">
            {index > 0 && (
              <Button variant="ghost" size="sm" onClick={() => setIndex((value) => value - 1)}>
                <ArrowLeft className="size-3.5" /> Back
              </Button>
            )}
            {last ? (
              <Button size="sm" onClick={finish}>
                Done <Check className="size-3.5" />
              </Button>
            ) : (
              <Button size="sm" onClick={() => setIndex((value) => value + 1)}>
                Next <ArrowRight className="size-3.5" />
              </Button>
            )}
          </div>
        </div>
      </section>
    </div>,
    document.body,
  )
}
