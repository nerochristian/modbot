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
  const adapter = new PrismaLibSql({
    url: process.env.DATABASE_URL ?? 'file:./dev.db',
  })
  return new PrismaClient({ adapter })
}

export const prisma = globalForPrisma.prisma ?? createClient()

if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.prisma = prisma
}
