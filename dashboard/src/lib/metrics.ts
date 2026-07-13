/**
 * Shared analytics range exports.
 *
 * Moderation metrics are sourced exclusively from the live bot PostgreSQL
 * database in `real-metrics.ts`; this compatibility module intentionally owns
 * no Prisma-backed metric or moderation queries.
 */
export { rangeDays } from '@/lib/dashboard-config'
export type { DateRange } from '@/lib/dashboard-config'
