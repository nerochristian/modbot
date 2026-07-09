import 'dotenv/config'
import path from 'node:path'
import { defineConfig, env } from '@prisma/config'

// Prisma 7 moved the datasource connection URL out of schema.prisma and into
// this config file. The CLI (db push / migrate / seed) reads the URL from here;
// the runtime PrismaClient connects via the libSQL driver adapter (see
// src/lib/prisma.ts).
export default defineConfig({
  schema: path.join('prisma', 'schema.prisma'),
  datasource: {
    url: env('DATABASE_URL'),
  },
  migrations: {
    seed: 'tsx prisma/seed.ts',
  },
})
