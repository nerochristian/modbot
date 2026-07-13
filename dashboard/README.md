# Docket dashboard

Docket is the production control plane for the Discord moderation bot in the parent repository. It is a Next.js 16 App Router application with Discord OAuth, per-server access control, live moderation data, and a separate dashboard identity store.

## Data ownership

- The bot PostgreSQL database is canonical for guild settings, cases, warnings, moderator notes, AutoMod telemetry, member risk data, appeals, moderation commands, audit events, and generated-report metadata.
- The dashboard SQLite/libSQL database stores Discord identities, revocable sessions, guild memberships, per-guild role grants, notifications, and user interface preferences.
- `BOT_DATABASE_URL` and `DASHBOARD_DATABASE_URL` must never point to the same database.

All operational APIs resolve the selected guild from an HttpOnly cookie and authorize it against an active `GuildMembership`. A global dashboard role does not grant access to another server.

## Supported workflows

- Discord OAuth with PKCE, one-time state, encrypted refresh tokens, and strict local return paths.
- Multi-server selection, including an install path for manageable servers where the bot is missing.
- Per-guild Admin, Moderator, and Helper roles with editable permissions.
- Live overview, analytics, members, cases, AutoMod configuration, activity, notifications, and team access.
- Idempotent moderation commands with pending, succeeded, and failed records. Discord failures remain auditable.
- One-time appeal links delivered by Discord DM, a public appeal form, staff review, and punishment reversal.
- Guild-scoped CSV, JSON, PDF, and XLSX reports generated from live bot data.

Billing, payment methods, third-party integrations, local passwords, and dashboard-owned 2FA are intentionally not exposed because no real provider is configured. Discord remains the only sign-in provider.

## Local setup

```powershell
cd C:\Users\Dell\mod\dashboard
npm ci
npm run db:migrate
npm run dev
```

The dashboard loads Discord and bot settings from the parent `.env`. Its own `.env` may contain a local dashboard store such as:

```dotenv
DATABASE_URL=file:./dev.db
```

Production should set the variables explicitly:

| Variable | Purpose |
| --- | --- |
| `DISCORD_TOKEN` | Bot API calls and guild discovery |
| `DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET` | Discord OAuth application |
| `DISCORD_TOKEN_ENCRYPTION_KEY` | Dedicated key for stored OAuth tokens |
| `SESSION_SECRET` or `AUTH_SECRET` | Session JWT signing |
| `DASHBOARD_PUBLIC_URL` | Exact public origin used by OAuth and appeal links |
| `DASHBOARD_DATABASE_URL` | Dashboard SQLite/libSQL store |
| `BOT_DATABASE_URL` | Bot PostgreSQL database |
| `OWNER_IDS` | Comma-separated platform owner Discord IDs |

The Discord application redirect URI must be `${DASHBOARD_PUBLIC_URL}/api/auth/discord/callback`.

## Validation

```powershell
npm test
npx prisma validate
npx tsc --noEmit --incremental false
npm run lint
npm run build
npm audit --omit=dev
```

The regression suite covers OAuth return-path safety, pagination validation, dashboard config validation, AutoMod runtime contracts, spreadsheet formula neutralization, and all four report artifact formats.

## Migrations and deployment

Tracked migrations live in `prisma/migrations`. The first migration describes the pre-tenancy schema; existing deployments baseline it once and then apply the forward guild-tenancy migration. Production deployment must use `prisma migrate deploy`—never `db push --accept-data-loss`.

`npm run build` emits `.next/standalone/server.js`. The root PM2 configuration launches that artifact as `modbot-dashboard`, keeps the dashboard database at `dashboard/data/dashboard.db`, and passes the bot PostgreSQL URL separately. The root deployment script migrates, builds, restarts the bot and dashboard, and verifies that the PM2 process exists.
