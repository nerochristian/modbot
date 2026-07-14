import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  FileClock,
  LogIn,
  MessageSquareWarning,
  ShieldCheck,
  Sparkles,
  TicketCheck,
} from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { LiveWire } from "@/components/marketing/live-wire";
import { CommandDemo } from "@/components/marketing/command-demo";
import { Faq } from "@/components/marketing/faq";

const FEATURES = [
  {
    icon: ShieldCheck,
    title: "Automod that explains itself",
    description:
      "Stop spam, scams, invite floods, slurs, mention storms, and raids with clear rules and visible actions.",
    detail:
      "Rules, bypass roles, thresholds, and punishments stay editable from one place.",
  },
  {
    icon: FileClock,
    title: "Every action has a record",
    description:
      "Warnings, timeouts, kicks, bans, evidence, and appeals stay attached to the member who received them.",
    detail: "No more searching old channels to learn what happened.",
  },
  {
    icon: MessageSquareWarning,
    title: "Reports reach the right staff",
    description:
      "Members can file private reports while staff review, resolve, and reopen them from Discord or the dashboard.",
    detail: "Reporter details remain inside the moderation workspace.",
  },
  {
    icon: TicketCheck,
    title: "Support without another bot",
    description:
      "Build ticket categories, custom questions, private channels, staff access, and transcripts around your server.",
    detail: "Every ticket flow uses the options your team configured.",
  },
];

const WORKFLOW = [
  {
    label: "Detect",
    title: "Docket catches the signal",
    text: "A rule, report, or moderator action enters one shared queue.",
  },
  {
    label: "Decide",
    title: "Your policy chooses the response",
    text: "Severity, staff permissions, bypass roles, and member history shape what happens next.",
  },
  {
    label: "Record",
    title: "The result stays readable",
    text: "The action, reason, evidence, actor, and Discord result become a durable case.",
  },
];

export default function LandingPage() {
  return (
    <>
      <section className="relative overflow-hidden px-5 pb-20 pt-16 sm:px-8 sm:pb-28 sm:pt-24">
        <div className="soft-grid pointer-events-none absolute inset-0 opacity-70" />
        <div className="blue-orb pointer-events-none absolute -right-24 -top-24 size-[36rem]" />
        <div className="relative mx-auto grid max-w-7xl items-center gap-14 xl:grid-cols-[0.92fr_1.08fr] xl:gap-20">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-accent-line bg-accent-soft px-3 py-1.5 text-sm font-medium text-accent">
              <span className="relative flex size-2">
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-info opacity-60" />
                <span className="relative inline-flex size-2 rounded-full bg-info" />
              </span>
              Discord moderation, finally organized
            </div>
            <h1 className="mt-7 font-display text-5xl font-semibold leading-[0.98] tracking-[-0.045em] text-foreground sm:text-6xl lg:text-7xl">
              Keep every server decision
              <span className="mt-2 block text-brand-gradient">
                in one place.
              </span>
            </h1>
            <p className="mt-7 max-w-xl text-lg leading-8 text-muted sm:text-xl">
              Docket combines automod, cases, reports, member history, tickets,
              and staff tools in one modern control center built around your
              Discord server.
            </p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/api/auth/discord/authorize"
                className={buttonVariants({
                  variant: "primary",
                  size: "lg",
                  className: "gap-2.5 px-7 shadow-xl shadow-blue-600/20",
                })}
              >
                <LogIn className="size-4.5" />
                Open with Discord
              </Link>
              <Link
                href="/commands"
                className={buttonVariants({
                  variant: "outline",
                  size: "lg",
                  className: "gap-2 px-7 bg-surface/40 backdrop-blur",
                })}
              >
                Explore commands <ArrowRight className="size-4" />
              </Link>
            </div>
            <div className="mt-8 flex flex-wrap gap-x-6 gap-y-3 text-sm text-muted">
              {[
                "Live Discord data",
                "Administrator-gated",
                "Every action recorded",
              ].map((item) => (
                <span key={item} className="inline-flex items-center gap-2">
                  <CheckCircle2 className="size-4 text-info" /> {item}
                </span>
              ))}
            </div>
          </div>

          <div className="relative mx-auto w-full max-w-2xl">
            <div className="absolute -inset-6 rounded-[2rem] bg-accent/10 blur-3xl" />
            <div className="glass-panel relative rounded-[1.6rem] p-3 sm:p-5">
              <div className="mb-4 flex items-center justify-between px-1">
                <div>
                  <p className="text-sm font-semibold text-foreground">
                    Live protection preview
                  </p>
                  <p className="mt-0.5 text-xs text-muted">
                    A raid enters. Docket contains it.
                  </p>
                </div>
                <span className="inline-flex items-center gap-2 rounded-full bg-success-soft px-3 py-1.5 text-xs font-semibold text-success">
                  <span className="size-1.5 rounded-full bg-success" /> Active
                </span>
              </div>
              <LiveWire />
            </div>
          </div>
        </div>
      </section>

      <section
        id="features"
        className="border-y border-border bg-surface/35 px-5 py-20 backdrop-blur-sm sm:px-8 sm:py-24"
      >
        <div className="mx-auto max-w-7xl">
          <div className="max-w-2xl">
            <p className="text-sm font-semibold text-accent">
              One workspace, the whole moderation shift
            </p>
            <h2 className="mt-3 font-display text-4xl font-semibold tracking-[-0.035em] text-foreground sm:text-5xl">
              Less bot clutter. More control.
            </h2>
            <p className="mt-4 text-lg leading-8 text-muted">
              The systems your team uses every day share the same members,
              permissions, records, and server context.
            </p>
          </div>
          <div className="mt-12 grid gap-4 md:grid-cols-2">
            {FEATURES.map((feature) => {
              const Icon = feature.icon;
              return (
                <article
                  key={feature.title}
                  className="lift-card group rounded-2xl border border-border bg-card/75 p-7 backdrop-blur"
                >
                  <div className="flex items-start gap-5">
                    <span className="grid size-12 shrink-0 place-items-center rounded-2xl border border-accent-line bg-accent-soft text-accent">
                      <Icon className="size-5" />
                    </span>
                    <div>
                      <h3 className="font-display text-xl font-semibold text-foreground">
                        {feature.title}
                      </h3>
                      <p className="mt-2 text-[15px] leading-7 text-muted">
                        {feature.description}
                      </p>
                      <p className="mt-4 border-t border-border pt-4 text-sm text-muted-2">
                        {feature.detail}
                      </p>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section
        id="pipeline"
        className="scroll-mt-24 px-5 py-20 sm:px-8 sm:py-28"
      >
        <div className="mx-auto max-w-7xl">
          <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
            <div className="max-w-2xl">
              <p className="text-sm font-semibold text-accent">
                A clear moderation loop
              </p>
              <h2 className="mt-3 font-display text-4xl font-semibold tracking-[-0.035em] text-foreground sm:text-5xl">
                From signal to record.
              </h2>
            </div>
            <p className="max-w-lg text-base leading-7 text-muted">
              Every step tells staff what happened, why it happened, and what
              still needs their attention.
            </p>
          </div>
          <div className="relative mt-12 grid gap-4 lg:grid-cols-3">
            <div className="absolute left-[16%] right-[16%] top-6 hidden h-px bg-gradient-to-r from-transparent via-accent/60 to-transparent lg:block" />
            {WORKFLOW.map((step, index) => (
              <article
                key={step.label}
                className="relative rounded-2xl border border-border bg-surface/60 p-7 backdrop-blur"
              >
                <span className="grid size-12 place-items-center rounded-full border border-accent-line bg-paper text-sm font-bold text-accent shadow-lg shadow-blue-950/40">
                  {index + 1}
                </span>
                <p className="mt-6 text-xs font-bold uppercase tracking-[0.16em] text-accent">
                  {step.label}
                </p>
                <h3 className="mt-2 font-display text-xl font-semibold text-foreground">
                  {step.title}
                </h3>
                <p className="mt-3 text-sm leading-7 text-muted">{step.text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="border-y border-border bg-surface/35 px-5 py-20 sm:px-8 sm:py-28">
        <div className="mx-auto grid max-w-7xl items-center gap-12 xl:grid-cols-[0.8fr_1.2fr] xl:gap-20">
          <div>
            <div className="inline-flex items-center gap-2 text-sm font-semibold text-accent">
              <Sparkles className="size-4" /> Member intelligence
            </div>
            <h2 className="mt-4 font-display text-4xl font-semibold tracking-[-0.035em] text-foreground sm:text-5xl">
              Open a member. See the full story.
            </h2>
            <p className="mt-5 text-lg leading-8 text-muted">
              Pull live Discord identity, roles, risk signals, warnings, cases,
              appeals, and staff notes without piecing together old messages.
            </p>
            <Link
              href="/commands"
              className={buttonVariants({
                variant: "subtle",
                size: "md",
                className: "mt-7 gap-2",
              })}
            >
              See every command <ArrowRight className="size-4" />
            </Link>
          </div>
          <div className="glass-panel overflow-hidden rounded-2xl p-2 sm:p-3">
            <CommandDemo />
          </div>
        </div>
      </section>

      <Faq />

      <section className="px-5 pb-24 pt-8 sm:px-8 sm:pb-28">
        <div className="relative mx-auto max-w-5xl overflow-hidden rounded-[2rem] border border-accent-line bg-gradient-to-br from-blue-600/20 via-card to-cyan-400/10 px-6 py-14 text-center shadow-2xl shadow-blue-950/30 sm:px-12 sm:py-20">
          <div className="blue-orb pointer-events-none absolute -right-24 -top-32 size-96" />
          <div className="relative">
            <p className="text-sm font-semibold text-info">
              Your next moderation shift can be simpler.
            </p>
            <h2 className="mx-auto mt-4 max-w-3xl font-display text-4xl font-semibold tracking-[-0.035em] text-foreground sm:text-5xl">
              Give your team one place to run the server.
            </h2>
            <p className="mx-auto mt-5 max-w-2xl text-lg leading-8 text-muted">
              Sign in with Discord, choose a server you administer, and
              configure Docket around the way your team actually works.
            </p>
            <Link
              href="/api/auth/discord/authorize"
              className={buttonVariants({
                variant: "primary",
                size: "lg",
                className: "mt-8 gap-2.5 px-8 shadow-xl shadow-blue-600/25",
              })}
            >
              <LogIn className="size-4.5" /> Open Docket
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
