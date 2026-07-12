'use client'

import { useEffect, useRef } from 'react'

/**
 * Circuit network — an ambient background that echoes the circuit traces in
 * the Docket logo. Blue nodes drift slowly; nearby nodes link with hairlines
 * that brighten as they approach, like a live signal graph. Rendered on a
 * canvas sized to its container, capped DPR, and paused for reduced-motion
 * (a static frame is drawn instead).
 */
export function CircuitField({ className }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const prefersReduced =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    let raf = 0
    let w = 0
    let h = 0
    const dpr = Math.min(window.devicePixelRatio || 1, 2)

    type Node = { x: number; y: number; vx: number; vy: number; r: number; pulse: number }
    let nodes: Node[] = []

    function seed() {
      const parent = canvas!.parentElement
      w = parent?.clientWidth ?? window.innerWidth
      h = parent?.clientHeight ?? 600
      canvas!.width = Math.round(w * dpr)
      canvas!.height = Math.round(h * dpr)
      canvas!.style.width = w + 'px'
      canvas!.style.height = h + 'px'
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)

      // Density scales with area but stays modest for performance.
      const count = Math.min(64, Math.round((w * h) / 22000))
      nodes = Array.from({ length: count }, (_, i) => ({
        // Deterministic-ish spread so SSR/first paint feels intentional.
        x: ((i * 97) % 100) / 100 * w,
        y: ((i * 53) % 100) / 100 * h,
        vx: (((i * 29) % 100) / 100 - 0.5) * 0.18,
        vy: (((i * 71) % 100) / 100 - 0.5) * 0.18,
        r: 1 + ((i * 13) % 100) / 100 * 1.4,
        pulse: ((i * 37) % 100) / 100,
      }))
    }

    const LINK_DIST = 130

    function draw(t: number) {
      ctx!.clearRect(0, 0, w, h)

      // Links first (under nodes).
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i]
          const b = nodes[j]
          const dx = a.x - b.x
          const dy = a.y - b.y
          const d = Math.hypot(dx, dy)
          if (d < LINK_DIST) {
            const alpha = (1 - d / LINK_DIST) * 0.32
            ctx!.strokeStyle = `rgba(46, 132, 255, ${alpha})`
            ctx!.lineWidth = 1
            ctx!.beginPath()
            ctx!.moveTo(a.x, a.y)
            ctx!.lineTo(b.x, b.y)
            ctx!.stroke()
          }
        }
      }

      // Nodes.
      for (const n of nodes) {
        const twinkle = 0.5 + 0.5 * Math.sin(t * 0.001 + n.pulse * 6.28)
        ctx!.beginPath()
        ctx!.arc(n.x, n.y, n.r, 0, Math.PI * 2)
        ctx!.fillStyle = `rgba(51, 214, 255, ${0.35 + twinkle * 0.5})`
        ctx!.fill()
      }
    }

    function step(t: number) {
      for (const n of nodes) {
        n.x += n.vx
        n.y += n.vy
        if (n.x < -20) n.x = w + 20
        if (n.x > w + 20) n.x = -20
        if (n.y < -20) n.y = h + 20
        if (n.y > h + 20) n.y = -20
      }
      draw(t)
      raf = requestAnimationFrame(step)
    }

    seed()
    if (prefersReduced) {
      draw(0) // one static frame
    } else {
      raf = requestAnimationFrame(step)
    }

    const onResize = () => {
      cancelAnimationFrame(raf)
      seed()
      if (prefersReduced) draw(0)
      else raf = requestAnimationFrame(step)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', onResize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className={className}
    />
  )
}
