import { PrismaClient } from '@prisma/client'
import { PrismaLibSql } from '@prisma/adapter-libsql'

// Prisma 7 connects through a driver adapter. We use libSQL, which speaks to a
// local SQLite file (file:./dev.db) with prebuilt binaries — no native build
// step required. To scale to a hosted libSQL/Turso or Postgres instance, swap
// the adapter and DATABASE_URL; nothing else in the app changes.
const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined
}

function createClient() {
  const url = process.env.DASHBOARD_DATABASE_URL ?? process.env.DATABASE_URL
  if (!url) {
    if (process.env.NODE_ENV === 'production') {
      throw new Error('DASHBOARD_DATABASE_URL is required in production')
    }
  } else if (!url.startsWith('file:') && !url.startsWith('libsql:')) {
    throw new Error('DASHBOARD_DATABASE_URL must use file: or libsql: with the configured adapter')
  }
  const adapter = new PrismaLibSql({
    url: url ?? 'file:./dev.db',
  })
  return new PrismaClient({ adapter })
}

export const prisma = globalForPrisma.prisma ?? createClient()

if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.prisma = prisma
}
