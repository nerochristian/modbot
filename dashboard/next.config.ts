import type { NextConfig } from 'next'
import path from 'node:path'
import dotenv from 'dotenv'

// Load environment variables from the project root .env so the dashboard
// inherits DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DATABASE_URL, etc.
dotenv.config({ path: path.resolve(__dirname, '../.env') })

const nextConfig: NextConfig = {
  // Pin the file-tracing root to this app so Next doesn't infer the parent
  // repository as the workspace root (it contains its own lockfile).
  outputFileTracingRoot: path.join(__dirname),
}

export default nextConfig
