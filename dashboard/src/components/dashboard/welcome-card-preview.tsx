'use client'

/**
 * Live mock of the bot's fixed 1024x500 welcome card. The background is the
 * only visual option; composition, ring, typography, and spacing stay uniform.
 */
export function WelcomeCardPreview({ values }: { values: Record<string, unknown> }) {
  const rawBackground = values.welcome_bg_url
  const backgroundUrl = typeof rawBackground === 'string' ? rawBackground.trim() : ''

  return (
    <div>
      <p className="mb-2 font-mono text-[0.625rem] font-bold uppercase tracking-[0.18em] text-accent">Live preview</p>
      <div className="relative aspect-[1024/500] w-full overflow-hidden border border-border bg-[#1a2436] shadow-lg">
        {backgroundUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={backgroundUrl} alt="" className="absolute inset-0 size-full object-cover" />
        ) : (
          <div className="absolute inset-0 bg-[linear-gradient(180deg,#466592_0%,#1a2137_100%)]" />
        )}

        <div className="absolute left-1/2 top-[10.2%] aspect-square w-[24.2%] -translate-x-1/2 rounded-full border-[clamp(4px,0.7vw,7px)] border-white bg-gradient-to-br from-slate-500 to-slate-800" />

        <div className="absolute inset-x-0 top-[63.8%] text-center text-white">
          <p
            className="font-display text-[clamp(1.75rem,7vw,4.75rem)] font-black leading-none tracking-[-0.045em]"
            style={{ textShadow: '5px 5px 2px rgba(0,0,0,.78)' }}
          >
            WELCOME
          </p>
          <p
            className="mt-[0.2%] truncate px-[5%] font-display text-[clamp(1rem,3.7vw,2.45rem)] font-black uppercase leading-none"
            style={{ textShadow: '3px 3px 2px rgba(0,0,0,.78)' }}
          >
            New Member
          </p>
        </div>
      </div>
      <p className="mt-2 text-xs text-muted-2">The member avatar and display name are inserted automatically. Use /welcome preview for the exact Discord render.</p>
    </div>
  )
}
