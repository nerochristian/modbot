import 'dotenv/config'
import path from 'node:path'
import { defineConfig, env } from '@prisma/config'

// Prisma 7 moved the datasource connection URL out of schema.prisma and into
// this config file. Migration commands read the URL here; the runtime client
// connects through the libSQL adapter (see src/lib/prisma.ts).
export default defineConfig({
  schema: path.join('prisma', 'schema.prisma'),
  datasource: {
    url: process.env.DASHBOARD_DATABASE_URL || env('DATABASE_URL'),
  },
})
