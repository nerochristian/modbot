import Link from 'next/link'
import {
  ShieldAlert,
  Gavel,
  Scale,
  Users2,
  SlidersHorizontal,
  Activity,
  Sparkles,
  LogIn,
} from 'lucide-react'
import { buttonVariants } from '@/components/ui/button'
import { HeroPreview } from '@/components/marketing/hero-preview'
import { Pricing } from '@/components/marketing/pricing'
import { Faq } from '@/components/marketing/faq'

const FEATURES = [
  { icon: ShieldAlert, title: 'Automod rule builder', desc: 'Compose layered rules for spam, slurs, invite links, mention floods, and raid patterns. Every rule scores content in real time and acts before your team ever sees it.' },
  { icon: Gavel, title: 'Case & infraction tracking', desc: 'Every warn, mute, kick, and ban becomes a case with full history, evidence, and moderator notes. Nothing gets lost between shifts.' },
  { icon: Scale, title: 'Appeals workflow', desc: 'Members submit appeals through a structured queue your team reviews, votes on, and resolves — so punishments stay fair and consistent.' },
  { icon: Users2, title: 'Member intelligence', desc: 'A complete profile for every member — join date, prior infractions, risk signals, and watchlist status — with server-side search, filters, and sorting.' },
  { icon: SlidersHorizontal, title: 'Roles & permissions', desc: 'Admin, Moderator, and Helper roles with an editable permission matrix. Access is enforced in the command deck and on every API route.' },
  { icon: Activity, title: 'Configurable command deck', desc: 'Reorder widgets, hide what you don’t need, pick severity thresholds, themes, and layout density. Every preference is saved to your account.' },
]

const STATS = [
  { value: '2.5M+', label: 'Messages scanned daily' },
  { value: '40k+', label: 'Communities protected' },
  { value: '180ms', label: 'Median action time' },
  { value: '99.99%', label: 'Uptime' },
]

const TESTIMONIALS = [
  { quote: 'Aegis caught a 300-account raid before a single message landed in general. Our mods woke up to a clean log instead of a cleanup.', name: 'Sarah Chen', title: 'Head Moderator, The Nexus', color: '#6e56f8' },
  { quote: 'The case system replaced a messy spreadsheet and three bots. Every mod sees the full history the moment they open a member.', name: 'Marcus Reid', title: 'Server Owner, Forge & Anvil', color: '#0ea5e9' },
  { quote: 'Appeals finally feel fair. The queue keeps every decision consistent, and members can see we actually reviewed them.', name: 'Priya Nair', title: 'Community Manager, Vela', color: '#22c55e' },
  { quote: 'Automod scoring cut our mod workload in half. The team spends time on people now, not deleting spam links.', name: 'Diego Santos', title: 'Head Mod, Kite Lounge', color: '#f43f5e' },
  { quote: 'The watchlist flags repeat offenders across alt accounts. We stop problems days before they escalate.', name: 'Emma Wagner', title: 'Owner, Nova Collective', color: '#8b5cf6' },
  { quote: 'Roles map exactly to how our team works — Helpers triage, Mods act, Admins configure. Onboarding a new mod takes minutes.', name: 'Kai Fischer', title: 'Admin, Drift Guild', color: '#f59e0b' },
]

export default function LandingPage() {
  return (
    <>
      {/* Hero — Command Deck Aesthetic */}
      <section className="relative overflow-hidden border-b border-border/60 bg-[#0a0a0f]">
        <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(#1f2937_0.6px,transparent_1px)] bg-[length:4px_4px] opacity-40" />
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-6 py-24 lg:grid-cols-2 lg:py-32">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1 text-xs font-medium tracking-[0.5px] text-white/70">
              <Sparkles className="size-3.5" /> NEW — AI content scoring v2
            </div>

            <h1 className="mt-6 text-6xl font-semibold tracking-[-2.5px] text-white sm:text-7xl">
              The command deck<br />for serious servers.
            </h1>
            <p className="mt-6 max-w-lg text-lg text-white/60">
              Aegis gives moderators a real-time, beautiful interface to stop raids, manage cases,
              and run their community with the precision of a war room.
            </p>

            <div className="mt-9 flex flex-wrap items-center gap-4">
              <Link
                href="/api/auth/discord/authorize"
                className={buttonVariants({ variant: 'primary', size: 'lg', className: 'gap-3 px-8 text-base' })}
              >
                <LogIn className="size-4" />
                Sign in with Discord
              </Link>
              <Link
                href="#features"
                className={buttonVariants({ variant: 'outline', size: 'lg', className: 'border-white/20 text-white hover:bg-white/5' })}
              >
                See how it works
              </Link>
            </div>

            <p className="mt-5 text-xs tracking-widest text-white/40">
              FREE FOR SERVERS UNDER 5K MEMBERS · NO CARD REQUIRED
            </p>
          </div>

          <div className="relative lg:pl-8">
            <div className="rounded-3xl border border-white/10 bg-[#111114] p-2 shadow-2xl">
              <HeroPreview />
            </div>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="border-b border-border/60 bg-[#0a0a0f] py-8">
        <div className="mx-auto grid max-w-6xl grid-cols-2 gap-y-8 px-6 text-center sm:grid-cols-4">
          {STATS.map((s, i) => (
            <div key={i} className="border-l border-white/10 pl-6 text-left first:border-l-0 first:pl-0">
              <div className="font-mono text-4xl font-semibold tracking-tighter text-white">{s.value}</div>
              <div className="mt-1 text-sm text-white/50">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="mx-auto max-w-6xl px-6 py-24">
        <div className="mb-12 text-center">
          <div className="text-xs font-medium tracking-[3px] text-accent">BUILT FOR POWER USERS</div>
          <h2 className="mt-3 text-5xl font-semibold tracking-[-1.5px]">Everything you need.<br />Nothing you don’t.</h2>
        </div>

        <div className="grid gap-px rounded-3xl border border-white/10 bg-white/5 md:grid-cols-2">
          {FEATURES.map((f, idx) => (
            <div key={idx} className="group flex gap-5 border-b border-white/10 p-8 last:border-b-0 md:border-r md:last:border-r-0">
              <div className="mt-1 text-accent"><f.icon className="size-6" /></div>
              <div>
                <div className="font-semibold tracking-tight text-lg">{f.title}</div>
                <p className="mt-2 text-sm leading-relaxed text-white/60">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Testimonials */}
      <section className="border-y border-white/10 bg-[#0a0a0f] py-20">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mb-10 text-center text-xs tracking-[3px] text-white/50">TRUSTED BY THE BEST</div>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {TESTIMONIALS.slice(0, 6).map((t, i) => (
              <figure key={i} className="rounded-2xl border border-white/10 bg-[#111114] p-8">
                <blockquote className="text-[15px] leading-snug text-white/90">“{t.quote}”</blockquote>
                <figcaption className="mt-6 flex items-center gap-3 text-sm">
                  <div className="size-9 rounded-full" style={{ backgroundColor: t.color }} />
                  <div>
                    <div className="font-medium text-white">{t.name}</div>
                    <div className="text-xs text-white/50">{t.title}</div>
                  </div>
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>

      <Pricing />
      <Faq />

      {/* Final CTA */}
      <section className="mx-auto max-w-4xl px-6 pb-24 pt-16 text-center">
        <h2 className="text-5xl font-semibold tracking-[-1.5px]">Ready to take control?</h2>
        <p className="mx-auto mt-4 max-w-md text-lg text-white/60">Sign in with Discord and add Aegis to your server in under 60 seconds.</p>

        <div className="mt-8 flex justify-center">
          <Link
            href="/api/auth/discord/authorize"
            className={buttonVariants({ variant: 'primary', size: 'lg', className: 'gap-3 px-10 text-lg' })}
          >
            <LogIn className="size-5" /> Sign in with Discord
          </Link>
        </div>
      </section>
    </>
  )
}
