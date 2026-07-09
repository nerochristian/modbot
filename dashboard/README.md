# Nebula — SaaS Analytics & Operations Dashboard

A complete, production-quality SaaS product: a polished marketing landing page plus a
full, multi-page, **fully configurable** dashboard with authentication, role-based
access control, a real backend (API routes + database), and realistic seed data.

Built with **Next.js 16 (App Router)**, **TypeScript**, **Tailwind CSS v4**,
**Prisma 7** (SQLite via the libSQL driver adapter), **jose** (JWT auth), and
**Recharts**.

> This is a self-contained demo product. All data is mock/seed data, structured so it
> can be swapped for a real database or external API without rewrites.

---

## Quick start

```bash
cd dashboard
npm install          # installs deps and generates the Prisma client (postinstall)
npm run db:reset     # creates the SQLite database and seeds realistic demo data
npm run dev          # start the dev server on http://localhost:3000
```

Then open **http://localhost:3000** and sign in with a demo account below.

### Demo accounts (password: `password123`)

| Email                | Role    | Access                                               |
| -------------------- | ------- | ---------------------------------------------------- |
| `admin@nebula.dev`   | Admin   | Everything, including the Admin panel                |
| `manager@nebula.dev` | Manager | Customers, users, reports, billing (read), settings  |
| `viewer@nebula.dev`  | Viewer  | Read-only dashboards, analytics, and reports         |

The login screen also has one-click demo buttons for each role.

---

## Scripts

| Script              | Description                                    |
| ------------------- | ---------------------------------------------- |
| `npm run dev`       | Start the development server                   |
| `npm run build`     | Production build                               |
| `npm run start`     | Run the production build                       |
| `npm run db:push`   | Sync the Prisma schema to the database         |
| `npm run db:seed`   | Seed the database with demo data               |
| `npm run db:reset`  | Reset the database and reseed (destructive)    |
| `npm run db:studio` | Open Prisma Studio to browse the data          |
| `npm run lint`      | Run ESLint                                     |

---

## Environment variables

Defaults live in `.env` and work out of the box for local development. For production,
override:

| Variable               | Description                                        | Default                 |
| ---------------------- | -------------------------------------------------- | ----------------------- |
| `DATABASE_URL`         | Database connection string                         | `file:./dev.db`         |
| `AUTH_SECRET`          | Secret used to sign session JWTs — **change this** | dev placeholder         |
| `AUTH_SESSION_TTL`     | Session lifetime in seconds                        | `604800` (7 days)       |
| `NEXT_PUBLIC_APP_NAME` | App display name                                   | `Nebula`                |
| `NEXT_PUBLIC_APP_URL`  | Public app URL                                     | `http://localhost:3000` |

---

## Features

### Marketing landing page
Hero, feature grid, configurable-dashboard spotlight, stats, testimonials, pricing
(monthly/annual toggle), FAQ accordion, CTA, and footer. Fully responsive with a
mobile nav, plus light/dark theme.

### Authentication & RBAC
- Email/password auth with **bcrypt** hashing and signed, **httpOnly** session
  cookies (JWT via `jose`).
- Server-side sessions with **revocation** (logout, logout-all-devices, password
  change) backed by a `Session` table.
- Route protection via Next.js `proxy.ts` (the v16 replacement for middleware).
- Three roles (**Admin / Manager / Viewer**) with an **editable permission matrix**
  stored in the database. Permissions are enforced **both** in the UI (hidden
  controls) and on **every API route**.

### Dashboard (10 pages)
Overview, Analytics, Customers, Users, Reports, Activity, Notifications, Billing,
Settings, and an Admin panel — with a collapsible sidebar, top bar, global
command-palette search (⌘K), notification center, and profile menu.

### Fully configurable
Every preference is persisted per-user to the backend (`DashboardConfig`):
- Show / hide / **reorder** dashboard widgets, and switch chart types per widget
- Theme (light / dark / system), **accent color**, and layout **density**
- Sidebar collapsed state, **auto-refresh interval**, default landing page
- Default **date range** and **export format**
- Per-table **visible columns** and reusable **saved views** (filters + sort)
- Notification preferences per category and channel

### Real, working backend
Server-side **search, filtering, sorting, and pagination** for every table; full CRUD
for customers, users, and reports; billing (plan changes, cancel/reactivate, invoices);
account management (profile, password, 2FA, active sessions); and an admin API for
roles, feature flags, the widget catalog, global settings, the audit log, and
broadcast notifications.

### UX states
Loading skeletons, empty states, error states with retry, confirmation modals, toast
notifications, and error boundaries throughout.

---

## Project structure

```
dashboard/
├── prisma/
│   ├── schema.prisma        # Data model (17 models)
│   └── seed.ts              # Deterministic, realistic seed data
├── prisma.config.ts         # Prisma 7 datasource config
├── src/
│   ├── proxy.ts             # Route protection (Next 16 "middleware")
│   ├── app/
│   │   ├── (marketing)/     # Landing page + layout
│   │   ├── (auth)/          # Login / register
│   │   ├── dashboard/       # All dashboard pages (nested layouts)
│   │   └── api/             # REST API routes (auth, analytics, CRUD, admin…)
│   ├── components/
│   │   ├── ui/              # Reusable design system (Button, Table, Modal…)
│   │   ├── charts/          # Recharts wrappers (theme-aware)
│   │   ├── dashboard/       # Shell, widgets, feature clients
│   │   ├── marketing/       # Landing sections
│   │   └── auth/            # Auth form
│   └── lib/                 # prisma, auth, rbac, session, api, store, config…
```

---

## Scaling to production

- **Database:** switch the Prisma datasource `provider` to `postgresql`, update
  `DATABASE_URL`, swap the driver adapter in `src/lib/prisma.ts` for the Postgres
  adapter, and run `npm run db:push`. No application code changes required.
- **Real data:** the API layer (`src/lib/metrics.ts` and the route handlers) is the
  single integration point — replace the seeded queries with your real data source.
- **Auth:** rotate `AUTH_SECRET`, keep `secure` cookies (automatic in production), and
  wire real email delivery for invites and password resets.

---

## Tech notes

- **Prisma 7** moves the datasource URL out of `schema.prisma` into `prisma.config.ts`
  and connects at runtime through a **driver adapter** (libSQL here, for
  zero-native-build local SQLite).
- **Next.js 16** renames `middleware` → `proxy` (Node runtime) and makes request APIs
  (`cookies`, `headers`, `params`, `searchParams`) fully async.
- **Tailwind v4** with a semantic token system enables runtime theme + accent
  switching.
