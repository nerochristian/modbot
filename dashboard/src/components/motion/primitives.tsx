'use client'

import { useEffect, useRef } from 'react'
import { animate, motion, MotionConfig, type Variants } from 'motion/react'

/** Global motion config: honor the OS reduced-motion preference everywhere. */
export function MotionRoot({ children }: { children: React.ReactNode }) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>
}

const EASE = [0.2, 0.8, 0.2, 1] as const

export function FadeIn({
  children,
  delay = 0,
  y = 10,
  className,
}: {
  children: React.ReactNode
  delay?: number
  y?: number
  className?: string
}) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  )
}

const staggerContainer: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.05 } },
}
const staggerItem: Variants = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: EASE } },
}

/** Staggered entrance for grids/lists: children rise in one after another. */
export function Stagger({ children, className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <motion.div className={className} variants={staggerContainer} initial="hidden" animate="show" {...props}>
      {children}
    </motion.div>
  )
}

export function StaggerItem({ children, className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <motion.div className={className} variants={staggerItem} {...props}>
      {children}
    </motion.div>
  )
}

/** Animated number: springs from 0 to `value` whenever it changes. */
export function CountUp({
  value,
  format = (v: number) => Math.round(v).toLocaleString(),
  className,
}: {
  value: number
  format?: (v: number) => string
  className?: string
}) {
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    const node = ref.current
    if (!node) return
    if (!Number.isFinite(value)) return
    const controls = animate(0, value, {
      duration: 0.9,
      ease: EASE,
      onUpdate: (latest) => {
        node.textContent = format(latest)
      },
    })
    return () => controls.stop()
  }, [format, value])

  return <span ref={ref} className={className} />
}
