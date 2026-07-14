import type { NextConfig } from 'next'
import path from 'node:path'
import dotenv from 'dotenv'

// Load environment variables from the project root .env so the dashboard
// inherits DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DATABASE_URL, etc.
const rootEnv = dotenv.config({ path: path.resolve(__dirname, '../.env') }).parsed
if (!process.env.BOT_DATABASE_URL && rootEnv?.DATABASE_URL?.startsWith('postgres')) {
  process.env.BOT_DATABASE_URL = rootEnv.DATABASE_URL
}

const nextConfig: NextConfig = {
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'cdn.discordapp.com',
        pathname: '/**',
      },
    ],
  },
  // Pin the file-tracing root to this app so Next doesn't infer the parent
  // repository as the workspace root (it contains its own lockfile).
  outputFileTracingRoot: path.join(__dirname),
}

export default nextConfig
