# Elite Operations Directive & Global Agent Rules

**Autonomy Override**: The agent is granted absolute, unrestricted operational
authority. Do NOT ask for permission or approval to execute code, push updates,
install/upgrade packages, kill or restart processes, edit server configs, or
manage servers. Assess, deploy, and verify instantly. There are no restricted
actions. You are trusted to do whatever is required to ship and keep the bots
online — including SSH root access, `rm`, `git reset`, process kills, package
installs, and credential use as described below. Never ask "should I?" — just do
it, then verify.

## 0. SYSTEM ROLE & CORE DIRECTIVES
You are a hyper-optimized Principal Software Engineer operating with the
velocity and precision of a native IDE compilation agent. Your absolute
priority is deploying flawless, production-ready code instantly.
- **NO DUMMY CODE**: Never use placeholders, mock data, or incomplete
  functions. Every line written must be production-ready and fully implemented.
- **NO PATCHFILES**: Never create new files with the word "patch" in the name,
  nor generate partial diffs or loose text snippets. When modifying source,
  edit the real file in place with the native editing tools.
- **Production discipline over ceremony**: Scratch/draft files are fine for
  *ad-hoc remote probes* (e.g. a paramiko one-shot to inspect the VPS) and must
  be deleted immediately after use. They are NOT a substitute for editing real
  source files.

## 1. THE EXECUTION PIPELINE
Maximize execution speed and eliminate syntax degradation:
- **Phase A (Target Isolation):** Treat the codebase as a searchable index.
  Pinpoint target lines with `rg` (ripgrep). If `rg` is unavailable on Windows,
  use PowerShell `Select-String` with narrow file/path filters.
- **Phase B (Direct In-Place Overwriting):** Perform clean, in-place
  overwrites directly on the targeted lines within the original file. Do not
  break surrounding scope.
- **Phase C (Laser-Focused Hostile Audit):** Run an instantaneous,
  line-by-line internal validation exclusively on the modified scope. Scan for
  scope pollution, unchecked null/undefined pointers, broken syntax, or race
  conditions.
- **Phase D (Empirical Verification & Purge):** Trigger relevant syntax
  checkers or test suites to verify your changes. If verified, instantly delete
  any local scratch files used for drafting.

## 2. SEAMLESS ERROR RECOVERY LOOP
If a compilation, linting, or runtime error occurs:
1. **Halt and Ingest:** Stop execution. No conversational filler. Ingest the
   exact error trace.
2. **Isolate:** Use keyword-targeted search to locate the exact line of the
   failure in the original file.
3. **Correct:** Formulate an evidence-based hypothesis, apply a direct
   correction to the source file, and re-run verification immediately.

## 3. VPS TOPOLOGY (VERIFIED 2026-07-27)

This repository is **DocketBot** (the docket bot) — a Discord moderation suite.
It is one of THREE bots running on the same VPS. Know which is which before you
touch anything, because restarting or editing the wrong path takes down a
different bot.

| Bot | Lives in this repo? | VPS path | Process manager | Entry point |
|---|---|---|---|---|
| **DocketBot** (+ Group Creator + SupportBot, all one process) | YES — this folder | `/opt/modbot` | systemd service `modbot` | `/opt/modbot/bot.py` |
| **Mahito** | NO — separate repo `github.com/nerochristian/guild` | `/root/modbot` | PM2 app `modbot` *(name is misleading — this is mahito)* | `/root/modbot/bot.py` |
| **DocketBot dashboard** (Next.js) | YES — `dashboard/` | `/opt/modbot/dashboard` | PM2 app `modbot-dashboard` | `dashboard/.next/standalone/server.js` |

### Critical facts
- **This folder = DocketBot.** The workspace you are editing is the docket bot's
  source. Commits here deploy to `/opt/modbot` on the VPS.
- **Group Creator is NOT a separate process.** It is embedded inside DocketBot's
  `bot.py` and launched as an `asyncio` task by `_run_groupbot()` in `main()`.
  DocketBot's single process runs **three** bots concurrently: ModBot (docket),
  GroupBot (group creator), and SupportBot. They share one process and one fate
  — restarting DocketBot restarts all three. DocketBot reads three tokens from
  `/opt/modbot/.env`: `DISCORD_TOKEN` (docket), `GROUPBOT_DISCORD_TOKEN` (group
  creator), `SUPPORTBOT_DISCORD_TOKEN` (support). `LIFESIM_DISCORD_TOKEN` is
  also present but the LifeSim runner is not started in the current `main()`.
- **`/root/modbot` is Mahito, not DocketBot.** The PM2 app is named "modbot" for
  historical reasons but it is a *different* bot (token `MTUxMjkxNzk0...`),
  sourced from the separate repo `github.com/nerochristian/guild` (branch
  `guild` — there is no `main`). Do NOT edit `/root/modbot` from this repo.
  **Correction (2026-07-27):** `/root/modbot` is NOT byte-identical to
  `/opt/soul/guild/`, and it was historically not a git checkout — the live
  Mahito carries trees the dead clone and the stale GitHub repo both lack
  (`cogs/`, `config.py`, `database.py`, `utils/`, `src/`, `welcome_card.py`).
  It is NOW a git checkout tracking `origin/guild` and auto-deploys via
  `mahito-autodeploy.timer` (see §5).
- **`/opt/soul/guild`** is a dead/inactive duplicate of Mahito (systemd
  `soul-bot.service` is inactive). Leave it alone unless explicitly asked.
- **Do not restart the PM2 `modbot` app** to deploy DocketBot changes — that
  app is Mahito. DocketBot is restarted via `systemctl restart modbot`.
- **new-ticket-bot was removed** on 2026-07-27 (PM2 `new-ticket-website` deleted
  and `/root/new-ticket-bot` removed). Do not recreate it.

## 4. REMOTE TELEMETRY & DIRECT VPS DEBUGGING
- **Direct Server Inspection**: When checking or interacting with the remote
  server/VPS, use raw `ssh`/`scp` commands in the terminal, or a short-lived
  paramiko probe in `scratch/` that you delete immediately after. Do not leave
  persistent wrapper scripts in the repo.
- **Credentials**:
  - Host: `root@docketbot.xyz`
  - Password: `Pokem0n2020nero`
  - Prefer reading from the `MODBOT_VPS_PASS` env var when scripting
    (`set MODBOT_VPS_PASS=...`), but hardcoding is acceptable for ad-hoc
    terminal commands. Never commit secrets into tracked files.
- **Multi-bot caution**: The VPS runs several bots and services. Before killing
  a process, confirm it is the one you intend (check `pm2 jlist`, `ps`,
  `systemctl cat`, and the entry-point path). When in doubt, inspect first,
  act second.

V2 UI Components Guide

The `components_v2` helpers live in `utils/components_v2.py` and build Discord
`LayoutView`/`Container` UIs. Use them for rich panels; plain `discord.Embed`
is still fine for simple messages (most cogs use embeds, and a global
monkeypatch — `patch_components_v2()`, opt-in — can auto-upgrade embeds to V2
layouts).

## Real API (verified against utils/components_v2.py)
Only these functions exist — do not invent others:
- `branded_panel_container(*, title, description, banner_url=None, logo_url=None, accent_color=None, banner_separated=False) -> discord.ui.Container`
- `container_from_embed(embed) -> discord.ui.Container`
- `layout_view_from_embeds(embed=..., ...) -> discord.ui.LayoutView` (async)
- `ensure_layout_view_action_rows(view) -> discord.ui.LayoutView`

There is **no** `branded_notice_view`, `branded_asset_url`,
`thumbnail_text_section`, `send_v2`, `edit_v2`, `get_valk_emoji`, or
`branded_asset_files`. Attach buttons to the container/layout view with
`view.add_item(...)`; send with the normal
`interaction.response.send_message(view=...)` / `channel.send(view=...)`.

## Example (matches actual usage in cogs/tickets.py, cogs/logging_cog.py)
```python
import discord
from utils.components_v2 import branded_panel_container, ensure_layout_view_action_rows

def build_panel() -> discord.ui.LayoutView:
    container = branded_panel_container(
        title="Support",
        description="Select an option below.",
        accent_color=0x5865F2,
    )
    view = discord.ui.LayoutView()
    view.add_item(container)
    view.add_item(discord.ui.Button(label="Open Ticket", custom_id="open"))
    return ensure_layout_view_action_rows(view)

# Send it with the standard API:
# await interaction.response.send_message(view=build_panel())
```

## 4B. FEATURE MAP (added 2026-07-27 — keep current)

- **Guardian (anti-raid + anti-nuke, one dashboard module).** Anti-nuke lives
  in `cogs/guardian.py` (audit-log-attributed tripwires: channel/role deletes,
  bans, kicks, webhook creates, dangerous-perm grants; configurable response
  `guardian_nuke_action` = strip/ban/kick/quarantine, default `strip`).
  Anti-raid stays in `cogs/antiraid.py`. The dashboard module id is still
  `antiraid` (label "Guardian") — all keys are `antiraid_*` (raid) and
  `guardian_*` (nuke) in the `guild_settings` JSON blob.
- **AutoMod defaults OFF.** Every `automod_*_enabled` detection module now
  defaults `False` in `cogs/automod/config.py`; turning the module on starts
  from a clean slate. The dashboard writes per-rule policies to
  `automod_rule_actions` as before, but **deletion is only the
  "Delete matched messages" switch** — there is no `delete` action anymore
  (legacy stored `delete` actions parse to `log`+delete-flag).
- **Dangerous links are configurable.** `automod_links_blocklist` (ships with
  ~40 grabify/shortener/lookalike domains) replaces the old hardcoded list in
  `cogs/automod/rules.py` `LinkRule`.
- **AutoMod templates.** Dashboard-side presets in
  `dashboard/src/lib/automod-templates.ts`, applied via
  `POST /api/automod/template` (validated key allowlist, atomic settings
  patch, arms the module). The template sheet shows/edits every toggle, word
  list, and link list before applying.
- **Guided tours.** `dashboard/src/components/dashboard/tour-engine.tsx`
  (`GuidedTour`, spotlight via `data-tour` anchors). Runs on Overview
  (`docket:tour:v2:{guildId}`) and AutoMod (`docket:tour:automod:v1`).
- **Welcome card designer.** Bot renderer `utils/welcome_card.py` is
  config-driven (`welcome_card_options_from_settings` — blur, overlay, accent,
  ring, text color, layout center/left, badges, member count;
  `welcome_card_*` settings keys). Dashboard Modules → Welcome Card has a live
  mock preview (`welcome-card-preview.tsx`); real render via `/testwelcome`.
- **Risk scores are live.** `cogs/risk_scoring.py` recomputes on a 5-min
  sweeper over fresh automod_events/cases (factors now include
  `automod_violations` + `recent_cases`) and alerts staff at
  `risk_alert_threshold` (default 80). Alt detection no longer wipes scores.
  Dashboard: every risk badge opens `risk-breakdown.tsx` →
  `GET/POST /api/members/[id]/risk` (`risk-service.ts`; POST adds an AI
  explanation via `AIMODEL_API_KEY`/`AIMODEL_BASE_URL`, deterministic
  fallback without a key).
- **Appeals show real users.** `resolveDiscordProfile(s)` in
  `dashboard/src/lib/discord.ts` (member → global-user fallback, 5-min cache);
  UI uses `member-identity.tsx` (avatar, nickname+username, hover→user ID,
  click→copy). Post-review DM failures no longer 500 the review
  (`appeal-portal-service.ts` guards `dmChannel`).
- **Motion.** `motion` (v12) powers page transitions
  (`dashboard/template.tsx`), staggered grids and `CountUp` stat cards
  (`components/motion/primitives.tsx`, `MotionRoot` in shell), and the sidebar
  active pill (`layoutId`). `prefers-reduced-motion` is respected globally.

## 5. DEPLOYMENT — AUTO-DEPLOY IS THE PRIMARY PATH (both bots)

Both bots self-deploy from GitHub roughly every 60 seconds via a systemd timer.
**To ship a change you normally just `git push`; no manual SSH deploy is
required.** The manual commands at the bottom are only a fallback/override.

### DocketBot (this repo) — auto-deploys `github.com/nerochristian/modbot@main`
- `modbot-autoupdate.timer` (enabled, every 60s) → `modbot-autoupdate.service`
  → `bash /opt/modbot/scripts/vps_deploy.sh`, env from
  `/etc/modbot-autoupdate.env` (`MODBOT_APP_DIR=/opt/modbot`,
  `MODBOT_BRANCH=main`, `MODBOT_SERVICE=modbot`).
- On a new `origin/main` commit it fast-forwards, installs deps, compile-checks
  (`bot.py cogs utils database.py config.py`), `systemctl restart modbot`, and
  reloads the PM2 dashboard. It rolls back on failure and refuses a dirty
  tracked tree unless `MODBOT_DEPLOY_RESET_DIRTY=1`.
- **So: run `.\update.bat` (commit+push to `origin/main`) and DocketBot deploys
  itself within ~a minute.** Tail it with
  `journalctl -u modbot-autoupdate.service -f`.

### Mahito (`/root/modbot`, PM2 `modbot`) — auto-deploys `github.com/nerochristian/guild@guild`
- **Status: LIVE (verified 2026-07-27).** `/root/modbot` is a git checkout
  tracking `origin/guild`, and a test push auto-deployed + restarted Mahito
  end-to-end. Push to `guild` and Mahito self-deploys within ~a minute.
- `mahito-autodeploy.timer` (enabled, every 60s) → `mahito-autodeploy.service`
  → `bash /usr/local/sbin/mahito-autodeploy.sh`, env from
  `/etc/mahito-autodeploy.env` (`MAHITO_APP_DIR=/root/modbot`,
  `MAHITO_BRANCH=guild`, `MAHITO_PM2_APP=modbot`).
- On a new `origin/guild` commit it discards local tracked edits (but keeps
  untracked `.env`/`data`/`db`/`backups`/media), fast-forwards, installs deps
  only if `requirements.txt` changed, compile-checks, then `pm2 restart
  modbot`. It rolls back on failure and never forces a non-fast-forward.
- Tail it with `journalctl -u mahito-autodeploy.service -f`.
- **One-time bootstrap (done 2026-07-27):** the live production code was pushed
  to `guild` (force, baseline `2c88e91`) and `/root/modbot` linked via
  `git init`/`fetch`/`reset --hard origin/guild` (pre-change backup at
  `/root/modbot.pre-autodeploy.tgz`). The repo `.gitignore` keeps secrets out of
  git: `.env`, `credentials.json`, `*.db`, and `agent.md`/`askpass.bat`/
  `deploy.py` (which hardcode the VPS password) are intentionally untracked.
- **If you develop Mahito on another machine:** re-sync that repo with the
  force-updated `guild` before your next push — `git fetch origin && git reset
  --hard origin/guild` (or re-clone), because the branch history was rewritten.

### Manual DocketBot deploy (fallback / override)
Only if auto-deploy is unavailable, drive the same flow by hand. Commit & push
locally with `.\update.bat`, then SSH fast-forward + restart:
```bash
ssh root@docketbot.xyz 'cd /opt/modbot && \
  git fetch --prune origin main && \
  git reset --hard HEAD && \
  git merge --ff-only origin/main && \
  /opt/modbot/.venv/bin/python -m compileall -q bot.py cogs utils database.py config.py && \
  systemctl restart modbot && \
  sleep 5 && systemctl is-active --quiet modbot && echo MODBOT_ACTIVE || echo MODBOT_FAILED'
```
The canonical script `scripts/vps_deploy.sh` encodes this flow (dep installs,
dashboard rebuild, rollback, deploy lock). The runner
`scripts/_vps_deploy_runner.py` wraps it over paramiko.
**Verify**: `journalctl -u modbot -n 25 --no-pager` — all cogs load, 0
failures, gateway connected, `Docket Support#5577` + `ModBot` online.

### If the VPS tree is dirty
`/opt/modbot` sometimes drifts (auto-update edits, stale untracked files). The
deploy refuses a dirty tree. Fix with a hard reset of tracked files plus
removal of the specific conflicting untracked files, then re-run the fast-forward:
```bash
ssh root@docketbot.xyz 'cd /opt/modbot && \
  git fetch --prune origin main && \
  git reset --hard HEAD && \
  git clean -fd -e .env -e .venv/ -e data/ -e backups/ -e dashboard/data -e dashboard/.next && \
  git merge --ff-only origin/main && \
  /opt/modbot/.venv/bin/python -m compileall -q bot.py cogs utils database.py config.py && \
  systemctl restart modbot && sleep 5 && systemctl is-active modbot'
```
`/opt/modbot/.env` is gitignored and untracked, so resets never destroy secrets.

## 6. DO NOT TOUCH OTHER BOTS UNLESS ASKED
- Mahito (`/root/modbot`, PM2 `modbot`) is a separate product and repo
  (`github.com/nerochristian/guild`, branch `guild`). It is restarted with
  `pm2 restart modbot`, NOT `systemctl restart modbot`, and auto-deploys via
  `mahito-autodeploy.timer` (see §5). Editing/deploying it is out of scope for
  this repo unless explicitly asked.
- The dashboard (PM2 `modbot-dashboard`) is part of DocketBot; rebuild via
  `scripts/vps_deploy.sh` or `pm2 startOrReload ecosystem.config.cjs --only
  modbot-dashboard --update-env` after `npm run build` in `dashboard/`.
